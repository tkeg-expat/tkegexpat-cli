from __future__ import annotations

import re
import sys

from .api import api_get, api_list
from .countries import id_to_abbr
from .cit import _dot, _reset_dots, _print_detail_table, _print_kv_table, DIM, RESET
from .entities import prime_name, entity_cell

# Read-only directory for the internal-team entity types (crm / rd / admin).
# Each: bare -> list all; <_id> -> detail. All resolve their name via
# `prime_entity` -> entity:prime.entity_name.

CONFIG = {
    "crm": {"type": "entity_crm", "label": "CRM Entities"},
    "rd": {"type": "entity_rd", "label": "RD Operator Entities"},
    "admin": {"type": "entity_admin", "label": "Admin Entities"},
}

LIST_COLUMNS = ["#", "Name", "Email", "Jurisdictions"]

# type-specific detail rows: (label, field, formatter)
_EXTRA = {
    "crm": [
        ("Languages", "authorized-language", "join"),
        ("Active", "active", "bool"),
        ("CRM Busy Rate", "crm-busy-rate", "raw"),
        ("Pending Leads", "pending-lead-number", "raw"),
        ("Pending Projects", "pending-project-number", "raw"),
    ],
    "rd": [
        ("Authorized Service", "authorized_service", "join"),
        ("RD Busy Rate", "rd-busy-rate", "raw"),
        ("On-going Items", "on-going-item-number", "raw"),
    ],
    "admin": [],
}

_last = {"kind": None, "records": []}


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _abbrs(v):
    a = [id_to_abbr(c) for c in _as_list(v)]
    return ", ".join(a) if a else "-"


def _join(v):
    parts = [str(x) for x in _as_list(v)]
    return ", ".join(parts) if parts else "-"


def _yes_no(v):
    return "Yes" if v is True else ("No" if v is False else "-")


def _points(rec):
    # admin's field name has a trailing space; crm/rd do not
    v = rec.get("available-points")
    if v is None:
        v = rec.get("available-points ")
    return str(v) if v is not None else "-"


def _user_name(uid):
    if not uid:
        return "-"
    try:
        return api_get(f"/api/1.1/obj/user/{uid}").get("response", {}).get("user_name") or str(uid)
    except Exception:
        return str(uid)


def _list_row(rec, i):
    return {
        "#": str(i),
        "Name": prime_name(rec.get("prime_entity")) or "-",
        "Email": rec.get("tkeg-expat-email") or "-",
        "Jurisdictions": _abbrs(rec.get("authorized_jurisdiction")),
    }


def cmd_entity(kind, args):
    cfg = CONFIG[kind]
    typ = cfg["type"]

    if args:
        raw = args[0].strip()
        if not re.fullmatch(r"\d+x\d+", raw):
            print(f"'{raw}' is not a bubble _id. Usage: {kind}   or   {kind} <_id>", file=sys.stderr)
            return
        try:
            rec = api_get(f"/api/1.1/obj/{typ}/{raw}").get("response", {})
        except Exception:
            rec = None
        if not rec or not rec.get("_id"):
            print(f"  No {kind} entity found with ID '{raw}'.", file=sys.stderr)
            return
        _render_entity_detail(kind, rec)
        return

    # bare -> list all
    print(f"  Fetching {cfg['label'].lower()} ...")
    records = api_list(typ)
    _last.update(kind=kind, records=records)
    if not records:
        print(f"\n  No {cfg['label'].lower()}.")
        return True
    print("  Resolving names ...")
    _reset_dots()
    print(f"\n{_dot(cfg['label'] + f' ({len(records)})')}")
    _print_detail_table([_list_row(r, i) for i, r in enumerate(records, 1)], LIST_COLUMNS)
    print(f"\n  {DIM}Open one: view <#>  or  {kind} <_id>{RESET}\n")
    return True


def cmd_view_dir(args):
    records = _last["records"]
    if not records:
        print("No entity list available. Run 'crm' / 'rd' / 'admin' first.", file=sys.stderr)
        return
    if not args:
        print("Usage: view <#>", file=sys.stderr)
        return
    try:
        idx = int(args[0])
    except ValueError:
        print(f"Invalid number: {args[0]}", file=sys.stderr)
        return
    if idx < 1 or idx > len(records):
        print(f"Invalid index. Choose 1-{len(records)}.", file=sys.stderr)
        return
    _render_entity_detail(_last["kind"], records[idx - 1])


def _fmt(rec, key, formatter):
    v = rec.get(key)
    if formatter == "join":
        return _join(v)
    if formatter == "bool":
        return _yes_no(v)
    return str(v) if v is not None else "-"


def _render_entity_detail(kind, rec):
    _reset_dots()
    name = prime_name(rec.get("prime_entity")) or "-"
    print("\n" + _dot(name))
    info = [
        ("Name", name),
        ("Entity _id", rec.get("_id")),
        ("Email", rec.get("tkeg-expat-email") or "-"),
        ("Portal User", _user_name(rec.get("portal_user"))),
        ("WeCom ID", rec.get("wecom_id") or "-"),
        ("Reports To", entity_cell(rec.get("direct_report_of"), "entity_admin") if rec.get("direct_report_of") else "-"),
        ("Jurisdictions", _abbrs(rec.get("authorized_jurisdiction"))),
        ("Available Points", _points(rec)),
    ]
    for label, key, formatter in _EXTRA.get(kind, []):
        info.append((label, _fmt(rec, key, formatter)))
    _print_kv_table(info)
    print()
