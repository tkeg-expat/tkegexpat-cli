from __future__ import annotations

import getpass
import subprocess
import sys
import time

from .auth import fetch_token, get_token, require_token
from .config import clear_credentials, load_credentials, save_credentials

REPO = "tkeg-expat/tkegexpat-cli"

AUTH_EXEMPT = {"login", "logout", "help", "update"}


def _ensure_auth(command: str, interactive: bool = False):
    if command in AUTH_EXEMPT:
        return
    try:
        token = require_token()
    except RuntimeError:
        msg = "Not logged in. Run: login" if interactive else "Not logged in. Run: tkegexpat login"
        print(msg, file=sys.stderr)
        if not interactive:
            sys.exit(1)
        raise
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
    creds = load_credentials()
    if not creds:
        print("Not logged in. Run: tkegexpat login")
        return

    print(f"Account: {creds['email']}")

    result = get_token()
    if result:
        remaining = result.get("expires_in", result["expires_at"] - int(time.time()))
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        print(f"Token:   valid ({result['source']}) — {hours}h {minutes}m remaining")
    else:
        print("Token:   expired or unavailable (will refresh on next request)")


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
    from .product import cmd_product as _product
    _product(args)


def cmd_help(args):
    from . import __version__
    print(
        f"""tkegexpat — TKEG Expat CLI v{__version__}

Commands:
  login          Log in with email and password
  logout         Clear saved credentials and token
  status         Show current auth status
  product <code> Query products (e.g. usci = US + company-incorporation)
  update         Update CLI to the latest version
  help           Show this help message

Product code format: <country><service>
  Country: 2-letter ISO code (us, gb, hk, sg, ie, ...)
  Service: ci ba ac co rm ra nd cs cd tr sl ar ca af os"""
    )


COMMANDS = {
    "login": cmd_login,
    "logout": cmd_logout,
    "status": cmd_status,
    "product": cmd_product,
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
        _ensure_auth(command, interactive=interactive)
    except RuntimeError:
        return
    handler(args)


def _interactive():
    from . import __version__
    print(f"tkegexpat v{__version__} — interactive mode")
    print("Type 'help' for commands, 'exit' to quit.\n")
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
        _run_command(command, parts[1:], interactive=True)


def main():
    args = sys.argv[1:]

    if not args:
        _interactive()
        return

    command = args[0]
    _run_command(command, args[1:])
