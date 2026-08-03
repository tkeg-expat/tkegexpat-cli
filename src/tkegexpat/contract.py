from __future__ import annotations

import re
import sys

from .api import api_get, api_list
from .cit import _dot, _reset_dots, _print_detail_table, _print_kv_table, DIM, RESET
from .i18n import wrap_display

# Shared contract script: backs the project detail view (render_contracts) and
# the standalone `contract` command (resolves by _id).

CONTRACT_COLUMNS = ["#", "Contract", "Status", "Value", "Generated", "Finalized"]
PARTY_COLUMNS = ["#", "Order", "Party"]

_current_contract = None  # last contract whose detail was shown (for `view-content`)


def _date(value):
    if not value:
        return "-"
    s = str(value)
    return s.split("T")[0] if "T" in s else s


def _money(value, currency):
    if isinstance(value, (int, float)):
        return f"{value:,.0f} {currency or ''}".strip()
    return "-"


def fetch_for_project(project_id):
    """All contracts whose associated project is `project_id`."""
    return api_list("contract:contract", [
        {"key": "associated-project-new", "constraint_type": "equals", "value": project_id},
    ])


def _row(c, i):
    return {
        "#": str(i),
        "Contract": c.get("contract-name") or "-",
        "Status": c.get("contract-status") or "-",
        "Value": _money(c.get("contract-value"), c.get("contract-currency")),
        "Generated": _date(c.get("contract-generation-date")),
        "Finalized": _date(c.get("contract-finalization-date")),
    }


def render_contracts(contracts):
    print(f"\n{_dot(f'Contracts ({len(contracts)})')}")
    if not contracts:
        print("  No contracts.")
        return
    _print_detail_table([_row(c, i) for i, c in enumerate(contracts, 1)], CONTRACT_COLUMNS)


# --- standalone `contract` command ------------------------------------------

def _classify_contract_input(raw: str) -> str:
    """'uid' for a Bubble _id, else 'invalid' — contracts resolve by _id only."""
    return "uid" if re.fullmatch(r"\d+x\d+", raw.strip()) else "invalid"


def _lookup_contract_by_id(value):
    print(f"  Looking up contract by ID: {value} ...")
    try:
        c = api_get(f"/api/1.1/obj/contract:contract/{value}").get("response", {})
    except Exception:
        c = None
    if not c or not c.get("_id"):
        print(f"  No contract found with ID '{value}'.", file=sys.stderr)
        return None
    return c


def cmd_contract(args):
    if not args:
        print("Usage: contract <_id>", file=sys.stderr)
        print("  contract 1777069271956x625453515163327900  open by its _id", file=sys.stderr)
        return
    raw = args[0].strip()
    if _classify_contract_input(raw) == "invalid":
        print(f"'{raw}' is not a contract _id. Contracts resolve by _id only.", file=sys.stderr)
        return
    c = _lookup_contract_by_id(raw)
    if c:
        _render_contract_detail(c)


def _party_row(pt, i):
    from .entities import prime_name
    ent = pt.get("party-entity")
    name = prime_name(ent) if ent else None
    order = pt.get("order")
    return {
        "#": str(i),
        "Order": str(order) if order is not None else "-",
        "Party": (f"{name}\n{ent}" if name else str(ent or "-")),
    }


def _render_contract_detail(c):
    global _current_contract
    from .entities import project_label
    _current_contract = c
    _reset_dots()

    print("\n" + _dot(c.get("contract-name") or "Contract"))
    info = [
        ("Contract Name", c.get("contract-name") or "-"),
        ("Status", c.get("contract-status") or "-"),
        ("Currency", c.get("contract-currency") or "-"),
        ("Value", _money(c.get("contract-value"), c.get("contract-currency"))),
        ("Generated", _date(c.get("contract-generation-date"))),
        ("Finalized", _date(c.get("contract-finalization-date"))),
        ("Associated Project", project_label(c.get("associated-project-new"))),
    ]
    _print_kv_table(info)

    print("\n  Fetching signing parties ...")
    try:
        parties = api_list("contract:singingparties", [
            {"key": "belonging-contract", "constraint_type": "equals", "value": c["_id"]},
        ])
    except Exception:
        parties = []
    parties.sort(key=lambda p: p.get("order") or 0)
    print(f"\n{_dot(f'Signing Parties ({len(parties)})')}")
    if not parties:
        print("  No signing parties.")
    else:
        _print_detail_table([_party_row(pt, i) for i, pt in enumerate(parties, 1)], PARTY_COLUMNS)

    from . import log
    log.set_context("contract", c["_id"], c.get("contract-name") or c["_id"])

    if (c.get("contract-text") or "").strip():
        print(f"\n  {DIM}Display the full contract text: view-content{RESET}")
    else:
        print()
    print(f"  {DIM}Show this contract's log: log{RESET}\n")


def cmd_view_content(args):
    if not _current_contract:
        print("No contract in view. Run 'contract <_id>' first.", file=sys.stderr)
        return
    text = _current_contract.get("contract-text") or ""
    if not text.strip():
        print("  This contract has no text content.")
        return
    _reset_dots()
    print("\n" + _dot((_current_contract.get("contract-name") or "Contract") + " — Content"))
    print()
    _print_contract_text(text)
    print()


def _print_contract_text(text):
    """Render the contract's BBCode body as readable, wrapped terminal text.

    Handles the tags contracts actually use: [h1]-[h3] headings, [b] bold,
    and nested [ml]/[ol]/[li indent=N] lists. Everything else is stripped."""
    s = text.replace("\r\n", "\n")

    # list items -> "<indent>• first line" with continuation lines aligned under it
    def _li(m):
        pad = "    " * int(m.group(1) or 0)
        lines = [ln.strip() for ln in m.group(2).strip().split("\n") if ln.strip()]
        if not lines:
            return "\n"
        out = f"\n{pad}• {lines[0]}"
        for ln in lines[1:]:
            out += f"\n{pad}  {ln}"
        return out
    s = re.sub(r"\[li(?:\s+indent=(\d+))?[^\]]*\](.*?)\[/li\]", _li, s, flags=re.S)

    # headings + bold -> plain text on their own lines
    s = re.sub(r"\[/?h[1-6][^\]]*\]", "\n", s)
    s = re.sub(r"\[/?b[^\]]*\]", "", s)
    # drop list containers and any remaining bbcode tags
    s = re.sub(r"\[/?(?:ml|ol|ul)[^\]]*\]", "", s)
    s = re.sub(r"\[/?[a-zA-Z][^\]]*\]", "", s)
    # collapse 3+ blank lines to one
    s = re.sub(r"\n[ \t]*(?:\n[ \t]*){2,}", "\n\n", s).strip("\n")

    try:
        import os
        tw = os.get_terminal_size().columns
    except (ValueError, OSError):
        tw = 80
    width = max(40, tw - 4)

    for line in s.split("\n"):
        content = line.strip()
        if not content:
            print()
            continue
        lead = len(line) - len(line.lstrip(" "))
        indent = " " * lead
        for i, piece in enumerate(wrap_display(content, max(20, width - lead))):
            print("  " + indent + ("  " if i else "") + piece)
