from __future__ import annotations

import getpass
import os
import re
import subprocess
import sys
import time
import urllib.request

from .auth import fetch_token, get_token
from .config import clear_credentials, load_credentials, save_credentials

REPO = "tkeg-expat/tkegexpat-cli"

AUTH_EXEMPT = {"login", "logout", "status", "help", "update", "tkeginfo"}

_last_view_context = "product"


def _prepare_command(command: str, interactive: bool = False):
    if command in AUTH_EXEMPT:
        return
    result = get_token()
    token = result["token"] if result else None
    from . import countries
    countries.sync(token)


def cmd_login(args):
    existing = load_credentials()
    if existing:
        print(f"Currently logged in as: {existing['email']}")
        answer = input("Re-login with different credentials? [y/N] ").strip().lower()
        if answer != "y":
            return

    email = input("Email: ").strip()
    if not email:
        print("Email cannot be empty.", file=sys.stderr)
        sys.exit(1)

    password = getpass.getpass("Password: ")
    if not password:
        print("Password cannot be empty.", file=sys.stderr)
        sys.exit(1)

    print("Authenticating...")
    try:
        result = fetch_token(email, password)
    except Exception as e:
        print(f"Login failed: {e}", file=sys.stderr)
        sys.exit(1)

    save_credentials(email, password)
    print(f"Logged in successfully. Token expires at {time.ctime(result['expires_at'])}.")


def cmd_logout(args):
    clear_credentials()
    print("Logged out. Credentials and token cleared.")


def cmd_user(args):
    from .user import cmd_user as _user
    _user(args)


def cmd_status(args):
    B = "\033[1m"
    D = "\033[2m"
    R = "\033[0m"
    creds = load_credentials()
    if not creds:
        print("Not logged in. Run: tkegexpat login")
        return

    print(f"  {D}Account{R}  {creds['email']}")

    result = get_token()
    if result:
        remaining = result.get("expires_in", result["expires_at"] - int(time.time()))
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        print(f"  {D}Token{R}    {B}valid{R} ({result['source']}) {D}—{R} {hours}h {minutes}m remaining")
    else:
        print(f"  {D}Token{R}    expired or unavailable (will refresh on next request)")


def cmd_update(args):
    print("Updating tkegexpat CLI...")
    url = f"git+https://github.com/{REPO}.git"
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", "--upgrade", url],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("Updated successfully.")
    else:
        print(f"Update failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)


def cmd_product(args):
    global _last_view_context
    from .product import cmd_product as _product
    _product(args)
    _last_view_context = "product"


def cmd_company(args):
    global _last_view_context
    from .company import cmd_company as _company
    result = _company(args)
    if result:
        _last_view_context = "company"


def cmd_tkeginfo(args):
    from .tkeginfo import cmd_tkeginfo as _tkeginfo
    _tkeginfo(args)


def cmd_cit(args):
    from .cit import cmd_cit as _cit
    _cit(args)


def cmd_vat(args):
    from .vat import cmd_vat as _vat
    _vat(args)


def cmd_legal_entity(args):
    global _last_view_context
    from .legal_entity import cmd_legal_entity as _le
    result = _le(args)
    if result:
        _last_view_context = "legal-entity"


def cmd_project(args):
    global _last_view_context
    from .project import cmd_project as _project
    result = _project(args)
    if result:
        _last_view_context = "project"


def cmd_project_item(args):
    global _last_view_context
    from .project_item import cmd_project_item as _pi
    result = _pi(args)
    if result:
        _last_view_context = "project-item"


def cmd_invoice(args):
    from .invoice import cmd_invoice as _inv
    _inv(args)


def cmd_contract(args):
    from .contract import cmd_contract as _con
    _con(args)


def cmd_view_content(args):
    from .contract import cmd_view_content as _vc
    _vc(args)


def cmd_message(args):
    from .message import cmd_message as _msg
    _msg(args)


def cmd_view_project_item(args):
    from .project import cmd_view_item as _f
    _f(args)


def cmd_view_invoice(args):
    from .project import cmd_view_invoice as _f
    _f(args)


def cmd_view_contract(args):
    from .project import cmd_view_contract as _f
    _f(args)


def cmd_cos(args):
    global _last_view_context
    from .cos import cmd_cos as _cos
    result = _cos(args)
    if result:
        _last_view_context = "cos"


def _entity_dir(kind, args):
    global _last_view_context
    from .entity_dir import cmd_entity
    if cmd_entity(kind, args):
        _last_view_context = "entity-dir"


def cmd_client(args):
    global _last_view_context
    from .client import cmd_client as _client
    result = _client(args)
    if result:
        _last_view_context = "client"


def cmd_crm(args):
    _entity_dir("crm", args)


def cmd_rd(args):
    _entity_dir("rd", args)


def cmd_admin(args):
    _entity_dir("admin", args)


def cmd_view(args):
    if _last_view_context == "legal-entity":
        from .legal_entity import cmd_view_entity as _view
    elif _last_view_context == "company":
        from .company import cmd_view_company as _view
    elif _last_view_context == "project":
        from .project import cmd_view_project as _view
    elif _last_view_context == "project-item":
        from .project_item import cmd_view_project_item as _view
    elif _last_view_context == "cos":
        from .cos import cmd_view_cos as _view
    elif _last_view_context == "entity-dir":
        from .entity_dir import cmd_view_dir as _view
    elif _last_view_context == "client":
        from .client import cmd_view_client as _view
    else:
        from .product import cmd_view_more as _view
    _view(args)


def cmd_view_product(args):
    global _last_view_context
    from .company import cmd_view_product as _vp
    _vp(args)
    _last_view_context = "product"


def cmd_resolve(args):
    from .product import cmd_resolve_requirement as _resolve
    _resolve(args)


def cmd_faq(args):
    from .product import cmd_faq as _faq
    _faq(args)


def cmd_help(args):
    from . import __version__
    B = "\033[1m"
    D = "\033[2m"
    R = "\033[0m"
    print(f"\n  {B}tkegexpat{R} {D}v{__version__}{R}\n")
    cmds = [
        ("login", "Log in with email and password"),
        ("logout", "Clear saved credentials and token"),
        ("status", "Show current auth status"),
        ("user", "Show the current logged-in user's profile"),
        ("product <code|slug|id>", "Products by code (usci), or open one by slug / _id"),
        ("company <country|id> [status]", "Managed companies by country, or open one by _id / TKEG company id"),
        ("project <code|id|slug>", "Projects by <country><service> code, or open one by _id / TKEG project id"),
        ("project-item <code> [status]", "Project items by <country><service> code (+ status), or open one by _id"),
        ("cos <code> [status]", "Check-out sessions by <country><service> code (+ status), or open one by _id"),
        ("invoice <invoice-id|_id>", "Open one invoice by its invoice-id or _id"),
        ("contract <_id>", "Open one contract by its _id"),
        ("view-project-item <#>", "Open an item from the project in view"),
        ("view-invoice <#>", "Open an invoice from the project in view"),
        ("view-contract <#>", "Open a contract from the project in view"),
        ("view-content", "Display the full text of the contract in view"),
        ("message [next]", "Messages for the project / company in view (paged)"),
        ("view <#>", "View details for the last listed items"),
        ("resolve <#>", "Resolve requirement products from the current product view"),
        ("faq", "Show FAQs from the current product view"),
        ("view-product <#>", "View product linked to a due date"),
        ("legal-entity <country>", "Legal entity types (e.g. legal-entity us)"),
        ("tkeginfo", "TKEG Expat's own group entities (name, address, active)"),
        ("crm / rd / admin [<_id>]", "Team entity directory — list all, or open one by _id"),
        ("client --crm <_id> | <_id|tkeg-id>", "Clients for a CRM, or open one (no bare list)"),
        ("cit <country>", "Corporate income tax info (e.g. cit us, cit hk)"),
        ("vat <country>", "VAT / sales tax rates (e.g. vat gb, vat sg)"),
        ("update", "Update CLI to the latest version"),
        ("help", "Show this help message"),
    ]
    cw = max(len(c) for c, _ in cmds)
    dw = max(len(d) for _, d in cmds)
    print(f"  {B}{'Command'.ljust(cw)} {D}│{R}{B} {'Description'.ljust(dw)}{R}")
    print(f"  {D}{'─' * cw}─┼─{'─' * dw}{R}")
    for c, d in cmds:
        print(f"  {c.ljust(cw)} {D}│{R} {d}")
    print(f"\n  {B}Product code format:{R} <country><service>")
    print(f"  {D}Country:{R} 2-letter ISO code (us, gb, hk, sg, ie, ...)")
    print(f"  {D}Service:{R} ci ba ac co rm ra nd cs cd tr sl ar ca af os")
    print(f"  {D}Or pass a product slug or _id to open that one product directly.{R}\n")


COMMANDS = {
    "login": cmd_login,
    "logout": cmd_logout,
    "status": cmd_status,
    "user": cmd_user,
    "product": cmd_product,
    "company": cmd_company,
    "project": cmd_project,
    "project-item": cmd_project_item,
    "cos": cmd_cos,
    "invoice": cmd_invoice,
    "contract": cmd_contract,
    "view-project-item": cmd_view_project_item,
    "view-invoice": cmd_view_invoice,
    "view-contract": cmd_view_contract,
    "view-content": cmd_view_content,
    "message": cmd_message,
    "view": cmd_view,
    "resolve": cmd_resolve,
    "faq": cmd_faq,
    "view-product": cmd_view_product,
    "legal-entity": cmd_legal_entity,
    "tkeginfo": cmd_tkeginfo,
    "crm": cmd_crm,
    "rd": cmd_rd,
    "admin": cmd_admin,
    "client": cmd_client,
    "cit": cmd_cit,
    "vat": cmd_vat,
    "update": cmd_update,
    "help": cmd_help,
}


def _run_command(command: str, args: list, interactive: bool = False):
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Type 'help' for available commands.", file=sys.stderr)
        return
    try:
        _prepare_command(command, interactive=interactive)
    except RuntimeError:
        return
    handler(args)


_B = "\033[1m"
_D = "\033[2m"
_R = "\033[0m"

_LOGO_RAW = """\
                     ████████████████████████████████████████ █
                   ██                                         ███
                 █                                            █████
                ████████████████   ██████████████████████████ ███████
                █   ███████████████                           ███████
                █     █ ███████████████                       ███████
                █     █     ███████████████                   ███████
                █     █         ██████████████                ███████
                █     █             ██████████████            ███████
                █     █                 ██████████████        ███████
                █     █                     ██████████████    ███████
                █     █                         █████████████ ███████
                ███████ ██████████████████████     ██████████████████
                      █                                ██████████████
                      █                                     █████████
                █████████████████████████████   █████████████ ███████
                █     █                      ██████████████   ███████
                █     █                  ██████████████       ███████
                █     █               █████████████           ███████
                █     █           ██████████████              ███████
                █     █       ██████████████                  ███████
                █     █    ██████████████                     ███████
                █     █ █████████████                         ██████
                █   █████████████                             ███████
                ███████████████ █████████████████████████████████████
                  ████████                                        █
                    ██                                          ██
                     ███████████████████████████████████████████"""
_LOGO_LINES = [line.rstrip() for line in _LOGO_RAW.split("\n")]
_min_indent = min(len(line) - len(line.lstrip()) for line in _LOGO_LINES if line.strip())
_LOGO_LINES = [line[_min_indent:] for line in _LOGO_LINES]
_LOGO_VISIBLE_WIDTH = max(len(line) for line in _LOGO_LINES)


def _interactive():
    from . import __version__
    mid = len(_LOGO_LINES) // 2
    text_lines = {
        mid - 1: f"{_B}TKEG EXPAT{_R}",
        mid:     f"{_D}v{__version__}{_R}",
        mid + 2: f"{_D}Type 'help' for commands{_R}",
        mid + 3: f"{_D}'exit' to quit{_R}",
    }
    print()
    for i, logo_line in enumerate(_LOGO_LINES):
        padded = logo_line.ljust(_LOGO_VISIBLE_WIDTH)
        right = text_lines.get(i, "")
        if right:
            print(f"{padded}  {right}")
        else:
            print(padded)
    print()
    while True:
        try:
            line = input("tkegexpat> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split()
        command = parts[0]
        if command in ("exit", "quit"):
            break
        if command == "restart":
            os.execv(sys.executable, [sys.executable] + sys.argv)
        _run_command(command, parts[1:], interactive=True)


def _auto_update():
    from . import __version__
    try:
        url = f"https://raw.githubusercontent.com/{REPO}/main/src/tkegexpat/__init__.py"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "tkegexpat-cli")
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read().decode()
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if not match:
            return
        remote = match.group(1)
        if _version_key(remote) <= _version_key(__version__):
            return
        print(f"  Updating v{__version__} → v{remote} ...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "--upgrade",
             f"git+https://github.com/{REPO}.git"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"  Updated. Restart to use v{remote}.")
        else:
            print(f"  Update failed.", file=sys.stderr)
    except Exception:
        pass


def _version_key(version: str) -> tuple:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def main():
    _auto_update()
    args = sys.argv[1:]

    if not args:
        _interactive()
        return

    command = args[0]
    _run_command(command, args[1:])
