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

AUTH_EXEMPT = {"login", "logout", "status", "help", "update"}

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


def cmd_view(args):
    if _last_view_context == "legal-entity":
        from .legal_entity import cmd_view_entity as _view
    elif _last_view_context == "company":
        from .company import cmd_view_company as _view
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
        ("product <code>", "Query products (e.g. usci = US + company-incorporation)"),
        ("company <country> [status]", "Managed companies (e.g. company us, company hk live)"),
        ("view <#>", "View details for the last listed items"),
        ("resolve <#>", "Resolve requirement products from the current product view"),
        ("faq", "Show FAQs from the current product view"),
        ("view-product <#>", "View product linked to a due date"),
        ("legal-entity <country>", "Legal entity types (e.g. legal-entity us)"),
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
    print(f"  {D}Service:{R} ci ba ac co rm ra nd cs cd tr sl ar ca af os\n")


COMMANDS = {
    "login": cmd_login,
    "logout": cmd_logout,
    "status": cmd_status,
    "product": cmd_product,
    "company": cmd_company,
    "view": cmd_view,
    "resolve": cmd_resolve,
    "faq": cmd_faq,
    "view-product": cmd_view_product,
    "legal-entity": cmd_legal_entity,
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
