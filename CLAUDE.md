# TKEG Expat CLI — Development Guide

Guidance for Claude Code working on the `tkegexpat` CLI.

## What this is

A Python CLI (`tkegexpat`) that gives TKEG Expat users authenticated access to the platform from the terminal. Installed from GitHub; self-updates via `tkegexpat update`.

- **Repo:** `https://github.com/tkeg-expat/tkegexpat-cli` (private)
- **Command:** `tkegexpat`
- **Python:** 3.9+ (system Python on macOS — use `from __future__ import annotations` and `typing.Optional`/`Tuple` instead of `dict | None` or `tuple[...]` syntax)

## Project structure

```
src/tkegexpat/
├── __init__.py    — version string (__version__)
├── cli.py         — entry point, command dispatch, auth gate
├── auth.py        — token fetch, cache check, auto-refresh logic
├── config.py      — credentials, token, settings, cache file paths
├── api.py         — authenticated API client (all calls require token)
├── countries.py   — country cache: sync from API, local storage, lookup by abbreviation
├── product.py     — product command: parse code, query, display table
└── i18n.py        — NEW2 multilingual field extraction via regex
```

- `pyproject.toml` / `setup.cfg` / `setup.py` — packaging (all three needed for pip 21.x compat)
- `.gitignore` — excludes __pycache__, eggs, dist, build

## Auth flow

1. `tkegexpat login` prompts for email + password
2. Credentials POST to `https://www.tkegexpat.cn/api/1.1/wf/get-red-queen-api` (same as Red Queen auth)
3. Token + expiry saved to `~/.config/tkegexpat/token.json` (0600 perms)
4. Credentials saved to `~/.config/tkegexpat/credentials.json` (0600 perms)
5. On any authenticated request, `get_token()` checks cache first — if valid (with 60s buffer), uses it; if expired, auto-refreshes using saved credentials
6. No manual re-login needed unless credentials change

## Install & update

```bash
# First install
pip3 install --user git+https://github.com/tkeg-expat/tkegexpat-cli.git

# Update (from CLI itself)
tkegexpat update

# PATH note: script installs to ~/Library/Python/3.9/bin/
# Add to ~/.zshrc if not on PATH:
#   export PATH="$HOME/Library/Python/3.9/bin:$PATH"
```

## Auth gate

Every command except `login`, `logout`, `help`, `update` requires auth. The `_ensure_auth()` function in `cli.py` enforces this before any handler runs. It also triggers `countries.sync()` so the country cache is always fresh.

All API calls go through `api.py` which calls `require_token()` — if the token is expired, it auto-refreshes using saved credentials. No token = error with login prompt.

## Adding new commands

1. Write the handler function in `cli.py` (or a new module if complex)
2. Add it to the `COMMANDS` dict in `cli.py`
3. Add it to the help text in `cmd_help()`
4. Auth is enforced automatically unless the command is in `AUTH_EXEMPT`
5. Use `api.api_get()` or `api.api_list()` for API calls — they handle auth
6. Use `countries.lookup(abbr)` to resolve country codes to Bubble IDs
7. Bump `__version__` in `__init__.py`
8. Update this file if the command adds a new capability area

## Dev workflow

- Edit files locally in `TKEG Expat CLI/`
- Test with `/Users/littlekeithy/Library/Python/3.9/bin/tkegexpat` (or reinstall from local: `pip3 install --user --force-reinstall --no-deps "path/to/TKEG Expat CLI"`)
- When ready: commit, push to `main`, then `tkegexpat update` pulls the latest

## Conventions

- Zero external dependencies — stdlib only (`json`, `urllib.request`, `getpass`, `subprocess`, etc.)
- All config files go in `~/.config/tkegexpat/` with 0600 permissions
- Sensitive values (passwords, tokens) never printed to stdout — use masked versions
- `REPO` constant in `cli.py` points to `tkeg-expat/tkegexpat-cli` for self-update
- User-Agent header set to `tkegexpat-cli/{version}` on all API requests
