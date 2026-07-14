from __future__ import annotations

import re
import sys

from .api import api_get, api_list
from .countries import id_to_abbr, lookup as country_lookup
from .cit import _dot, _reset_dots, _print_detail_table, _print_kv_table, DIM, RESET
from .product import SERVICE_TYPES, SERVICE_TYPE_TO_CODE, parse_code

# Shared project-item script: backs both the project detail view (render_items)
# and the standalone `project-item` command.

ITEM_COLUMNS = ["#", "Item", "Svc", "Qty", "Status", "Start", "End", "Price"]

# item_status option set (distinct from a project's `data: status (Selected)`).
STATUS_OPTIONS = ["Completed", "Lost", "Paused", "Refunded", "Credit"]

_last_items = []


def _money(value, currency):
    if isinstance(value, (int, float)):
        return f"{value:,.0f} {currency or ''}".strip()
    return "-"


def _date(value):
    if not value:
        return "-"
    s = str(value)
    return s.split("T")[0] if "T" in s else s


def fetch_for_project(project_id):
    """All project items whose belonging project is `project_id`."""
    return api_list("project:projectitem", [
        {"key": "project: belonging-project", "constraint_type": "equals", "value": project_id},
    ])


def latest_end_date(items):
    """Latest item `end_date` across `items` (ISO strings sort chronologically),
    used as the derived project-level end date. None if no item has an end date."""
    ends = [it.get("end_date") for it in items if it.get("end_date")]
    return max(ends) if ends else None


def _row(it, i):
    svc = it.get("service_type")
    price = it.get("price: total: tax-included")
    if price is None:
        price = it.get("price: single")
    qty = it.get("item_quantity")
    return {
        "#": str(i),
        "Item": it.get("item_name") or "-",
        "Svc": (SERVICE_TYPE_TO_CODE.get(svc, svc) if svc else "-") or "-",
        "Qty": str(qty) if qty is not None else "-",
        "Status": it.get("item_status") or "-",
        "Start": _date(it.get("starting_date")),
        "End": _date(it.get("end_date")),
        "Price": _money(price, it.get("price: marking_currency")),
    }


def _print_item_table(items, header):
    print(f"\n{_dot(header)}")
    if not items:
        print("  No project items.")
        return
    _print_detail_table([_row(it, i) for i, it in enumerate(items, 1)], ITEM_COLUMNS)


def render_items(items):
    """Section renderer used inside the project detail view."""
    _print_item_table(items, f"Project Items ({len(items)})")


# --- standalone `project-item` command --------------------------------------

def _classify_item_input(raw: str) -> str:
    """'uid' for a Bubble _id, 'code' for <country><service> (e.g. usci), else
    'invalid' — project items have no numeric human id."""
    s = raw.strip()
    if re.fullmatch(r"\d+x\d+", s):
        return "uid"
    if "-" not in s and len(s) >= 4:
        if SERVICE_TYPES.get(s[-2:].lower()) and country_lookup(s[:-2]):
            return "code"
    return "invalid"


def _lookup_item_by_id(value):
    print(f"  Looking up project item by ID: {value} ...")
    try:
        it = api_get(f"/api/1.1/obj/project:projectitem/{value}").get("response", {})
    except Exception:
        it = None
    if not it or not it.get("_id"):
        print(f"  No project item found with ID '{value}'.", file=sys.stderr)
        return None
    return it


def cmd_project_item(args):
    global _last_items
    _last_items = []

    from .filters import parse_filters
    positional, extra, ok = parse_filters(args, crm_field="data: crm", client_field="data: client")
    if not ok:
        return

    if not positional:
        print("Usage: project-item <code> [status]  [--crm <_id>] [--client <_id|tkeg-id>]   |   project-item <id>", file=sys.stderr)
        print("  project-item usci                         list US company-incorporation items", file=sys.stderr)
        print("  project-item usci completed --crm <_id>   filtered by status + CRM", file=sys.stderr)
        print("  project-item 1711510007997x965481436808478700   open one item by its _id", file=sys.stderr)
        print(f"\n  status option set: {', '.join(STATUS_OPTIONS)}", file=sys.stderr)
        print(f"  service type codes: {', '.join(sorted(SERVICE_TYPES))}", file=sys.stderr)
        return

    raw = positional[0].strip()
    kind = _classify_item_input(raw)

    if kind == "uid":
        if extra:
            print(f"  {DIM}(--crm/--client ignored for direct lookup){RESET}")
        it = _lookup_item_by_id(raw)
        if not it:
            return
        _last_items = [it]
        _render_item_detail(it)
        return True

    if kind == "invalid":
        print(f"'{raw}' is not a <country><service> code or an item _id.", file=sys.stderr)
        print(f"  e.g. project-item usci   or   project-item <_id>", file=sys.stderr)
        return

    # code: <country><service> [status] -> list
    country, service_type = parse_code(raw.lower())
    status_filter = " ".join(positional[1:]).lower() if len(positional) > 1 else None
    label = f"{country['abbr']} + {service_type}" + (f" — {status_filter}" if status_filter else "")
    print(f"  Fetching project items: {label} ...")

    items = api_list("project:projectitem", [
        {"key": "country_region", "constraint_type": "equals", "value": country["_id"]},
        {"key": "service_type", "constraint_type": "equals", "value": service_type},
    ] + extra)
    if status_filter:
        items = [it for it in items if (it.get("item_status") or "").lower() == status_filter]
    _last_items = items

    if not items:
        print(f"\n  No project items found for {label}.")
        return True

    _print_item_table(items, f"{label} — Project Items ({len(items)})")
    print(f"\n  {DIM}View full item: view <#>{RESET}\n")
    return True


def cmd_view_project_item(args):
    if not _last_items:
        print("No project-item list available. Run 'project-item <code>' first.", file=sys.stderr)
        return
    if not args:
        print("Usage: view <#>", file=sys.stderr)
        return
    try:
        idx = int(args[0])
    except ValueError:
        print(f"Invalid number: {args[0]}", file=sys.stderr)
        return
    if idx < 1 or idx > len(_last_items):
        print(f"Invalid index. Choose 1-{len(_last_items)}.", file=sys.stderr)
        return
    _render_item_detail(_last_items[idx - 1])


def _resolve_project_label(proj_id):
    if not proj_id:
        return "-"
    try:
        pr = api_get(f"/api/1.1/obj/projects:all/{proj_id}").get("response", {})
    except Exception:
        return str(proj_id)
    name = pr.get("project_name") or "-"
    tid = pr.get("tkeg_project_id")
    tail = f"  (TKEG {tid})" if tid else ""
    return f"{name}{tail}\n{proj_id}"


def _resolve_product_name(prod_id):
    if not prod_id:
        return "-"
    from .config import effective_language
    from .i18n import extract_lang, strip_markup
    try:
        pr = api_get(f"/api/1.1/obj/product:all/{prod_id}").get("response", {})
    except Exception:
        return str(prod_id)
    raw = pr.get("product-name-new2") or ""
    lang = effective_language()
    ext = extract_lang(raw, lang) if lang else None
    return strip_markup(ext) if ext else (strip_markup(raw) if raw else "-")


def _render_item_detail(it):
    from .entities import entity_cell
    _reset_dots()

    svc = it.get("service_type")
    cur = it.get("price: marking_currency")
    qty = it.get("item_quantity")
    pts = it.get("points: redemption value")

    print(f"\n{_dot(it.get('item_name') or 'Project Item')}")
    info = [
        ("Item Name", it.get("item_name") or "-"),
        ("Status", it.get("item_status") or "-"),
        ("Service", (SERVICE_TYPE_TO_CODE.get(svc, svc) if svc else "-") or "-"),
        ("Country", id_to_abbr(it.get("country_region") or "")),
        ("Quantity", str(qty) if qty is not None else "-"),
        ("Start Date", _date(it.get("starting_date"))),
        ("End Date", _date(it.get("end_date"))),
        ("Belonging Project", _resolve_project_label(it.get("project: belonging-project"))),
        ("Product", _resolve_product_name(it.get("item_product"))),
        ("Price (single)", _money(it.get("price: single"), cur)),
        ("Price (pre-tax)", _money(it.get("price: total: tax-excluded"), cur)),
        ("Tax", _money(it.get("price: tax: total (New)"), cur)),
        ("Price (tax-incl)", _money(it.get("price: total: tax-included"), cur)),
        ("Cost (tax-incl)", _money(it.get("cost: total: tax-included: marking currency"), it.get("cost: marking_currency"))),
        ("Profit (USD)", _money(it.get("Finalization: USD Profit"), "USD")),
        ("Points Redemption", str(pts) if pts is not None else "-"),
        ("Client", entity_cell(it.get("data: client"), "entity_client")),
        ("CRM", entity_cell(it.get("data: crm"), "entity_crm")),
        ("Supplier", entity_cell(it.get("supplier_entity"), "entity_supplier")),
        ("RD Operator", entity_cell(it.get("rd-entity"), "entity_rd")),
    ]
    _print_kv_table(info)

    proj_id = it.get("project: belonging-project")
    if proj_id:
        from . import message
        message.set_context("project", proj_id, f"item: {it.get('item_name') or '-'}")
        print(f"\n  {DIM}Messages for the belonging project: message{RESET}")
    print()
