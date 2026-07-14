from __future__ import annotations

import re
import sys

from .api import api_get, api_list
from .cit import _dot, _reset_dots, _print_detail_table, _print_kv_table, DIM, RESET
from .entities import prime_name, entity_cell

# Read-only client viewer. There are ~660 clients, so there is NO bare list —
# scope by CRM (`client --crm <_id>`) or open one (`client <_id | tkeg-id>`).
# entity_client.Slug == the client's TKEG id.

LIST_COLUMNS = ["#", "Name", "TKEG id", "Active"]

_last_clients = []


def _yes_no(v):
    return "Yes" if v is True else ("No" if v is False else "-")


def _num(v):
    return str(v) if v is not None else "-"


def _batch_prime_names(prime_ids):
    """{prime_id: entity_name} resolved in one query per 100 via the `in` constraint."""
    names = {}
    ids = [p for p in prime_ids if p]
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        try:
            rows = api_list("entity:prime", [
                {"key": "_id", "constraint_type": "in", "value": chunk},
            ])
        except Exception:
            rows = []
        for r in rows:
            names[r["_id"]] = r.get("entity_name")
    return names


def _resolve_client(value):
    """entity_client _id -> itself; numeric tkeg id -> _id via Slug."""
    value = value.strip()
    if re.fullmatch(r"\d+x\d+", value):
        return value
    try:
        rows = api_list("entity_client", [
            {"key": "Slug", "constraint_type": "equals", "value": value},
        ])
    except Exception:
        rows = []
    return rows[0]["_id"] if rows else None


def _lookup_client_by_id(cid):
    try:
        c = api_get(f"/api/1.1/obj/entity_client/{cid}").get("response", {})
    except Exception:
        c = None
    if not c or not c.get("_id"):
        print(f"  No client found with ID '{cid}'.", file=sys.stderr)
        return None
    return c


def cmd_client(args):
    global _last_clients
    _last_clients = []

    from .filters import parse_filters
    positional, extra, ok = parse_filters(args, crm_field="belonging_crm")
    if not ok:
        return

    # detail: client <_id | tkeg-id>
    if positional:
        raw = positional[0].strip()
        cid = _resolve_client(raw)
        if not cid:
            print(f"  No client found for '{raw}'.", file=sys.stderr)
            return
        c = _lookup_client_by_id(cid)
        if not c:
            return
        _last_clients = [c]
        _render_client_detail(c)
        return

    # list: client --crm <_id>  (no bare list — too many clients)
    if not extra:
        print("Usage: client --crm <_id>   |   client <_id | tkeg-id>", file=sys.stderr)
        print("  (no bare list — there are ~660 clients; scope by CRM or open one by id)", file=sys.stderr)
        return

    print("  Fetching clients ...")
    clients = api_list("entity_client", extra)
    _last_clients = clients
    if not clients:
        print("\n  No clients found for that CRM.")
        return True

    print("  Resolving names ...")
    names = _batch_prime_names([c.get("prime_entity") for c in clients])
    _reset_dots()
    print(f"\n{_dot(f'Clients ({len(clients)})')}")
    rows = [{
        "#": str(i),
        "Name": names.get(c.get("prime_entity")) or "-",
        "TKEG id": c.get("Slug") or "-",
        "Active": _yes_no(c.get("active-client")),
    } for i, c in enumerate(clients, 1)]
    _print_detail_table(rows, LIST_COLUMNS)
    print(f"\n  {DIM}Open one: view <#>  or  client <_id | tkeg-id>{RESET}\n")
    return True


def cmd_view_client(args):
    if not _last_clients:
        print("No client list available. Run 'client --crm <_id>' first.", file=sys.stderr)
        return
    if not args:
        print("Usage: view <#>", file=sys.stderr)
        return
    try:
        idx = int(args[0])
    except ValueError:
        print(f"Invalid number: {args[0]}", file=sys.stderr)
        return
    if idx < 1 or idx > len(_last_clients):
        print(f"Invalid index. Choose 1-{len(_last_clients)}.", file=sys.stderr)
        return
    _render_client_detail(_last_clients[idx - 1])


def _render_client_detail(c):
    _reset_dots()
    name = prime_name(c.get("prime_entity")) or "-"
    users = c.get("user_account")
    users_txt = ", ".join(users) if isinstance(users, list) else (str(users) if users else "-")

    print("\n" + _dot(name))
    info = [
        ("Name", name),
        ("Client _id", c.get("_id")),
        ("TKEG id (Slug)", c.get("Slug") or "-"),
        ("Belonging CRM", entity_cell(c.get("belonging_crm"), "entity_crm")),
        ("TKEG Entity", entity_cell(c.get("belonging-tkeg-expat-entity"), "entity:tkegexpat")),
        ("Active", _yes_no(c.get("active-client"))),
        ("Miles", _num(c.get("miles"))),
        ("Total Qualifying Points", _num(c.get("total_qualifying_points"))),
        ("This-Year Qualifying Projects", _num(c.get("current_year_qualifying_project"))),
        ("User Account(s)", users_txt),
    ]
    _print_kv_table(info)
    print()
