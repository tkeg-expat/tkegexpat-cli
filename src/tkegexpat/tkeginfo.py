from __future__ import annotations

from .api import api_get, api_list
from .cit import _dot, _reset_dots, _print_detail_table

# TKEG Expat's own group legal entities. Each record links to a master
# entity:prime record (holding the canonical name + address) and carries an
# `active` flag. These records also hold Stripe keys / bank details — we read
# only name / address / active and never touch those.
TKEGEXPAT_TYPE = "entity:tkegexpat"
PRIME_FIELD = "element: prime entity"

TABLE_COLUMNS = ["#", "Name", "Address", "Active"]


def _resolve_prime(prime_id):
    if not prime_id:
        return {}
    try:
        rec = api_get(f"/api/1.1/obj/entity:prime/{prime_id}")
        return rec.get("response", rec)
    except Exception:
        return {}


def _format_address(value):
    if not value:
        return "-"
    if isinstance(value, dict):
        return value.get("address") or str(value)
    return str(value) or "-"


def cmd_tkeginfo(args):
    print("  Fetching TKEG Expat group entities ...")
    entities = api_list(TKEGEXPAT_TYPE)

    if not entities:
        print("\n  No entities found.")
        return

    print("  Resolving names ...")
    resolved = []
    for e in entities:
        prime = _resolve_prime(e.get(PRIME_FIELD))
        resolved.append({
            "name": prime.get("entity_name") or "-",
            "address": _format_address(prime.get("entity_address")),
            "active": bool(e.get("active")),
        })

    # Active firms first, then alphabetical by name.
    resolved.sort(key=lambda r: (not r["active"], r["name"].lower()))

    rows = []
    for i, r in enumerate(resolved, 1):
        rows.append({
            "#": str(i),
            "Name": r["name"],
            "Address": r["address"],
            "Active": "Yes" if r["active"] else "No",
        })

    active_count = sum(1 for r in resolved if r["active"])

    _reset_dots()
    print(f"\n{_dot(f'TKEG Expat — Group Entities ({len(resolved)}, {active_count} active)')}")
    _print_detail_table(rows, TABLE_COLUMNS)
    print()
    return True
