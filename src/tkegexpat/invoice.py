from __future__ import annotations

import re
import sys

from .api import api_get, api_list
from .cit import _dot, _reset_dots, _print_detail_table, _print_kv_table, DIM, RESET

# Shared invoice script: backs the project detail view (render_invoices) and the
# standalone `invoice` command (resolves by tkeg invoice-id or _id).

INVOICE_COLUMNS = ["#", "Invoice ID", "Status", "Pre-Tax", "Tax", "Total", "Issued"]
LINE_ITEM_COLUMNS = ["#", "Product", "Qty", "Unit", "Pre-Tax", "Tax", "Total"]


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
    """All invoices whose belonging project is `project_id`."""
    return api_list("project:invoice", [
        {"key": "belonging projects new", "constraint_type": "equals", "value": project_id},
    ])


def _row(inv, i):
    cur = inv.get("invoice currency")
    return {
        "#": str(i),
        "Invoice ID": str(inv.get("invoice-id") or "-"),
        "Status": inv.get("invoice-status") or "-",
        "Pre-Tax": _money(inv.get("invoice-total-pre-tax-value"), cur),
        "Tax": _money(inv.get("invoice-total-tax-value"), cur),
        "Total": _money(inv.get("invoice-total-value-tax-included"), cur),
        "Issued": _date(inv.get("issuing date")),
    }


def render_invoices(invoices):
    print(f"\n{_dot(f'Invoices ({len(invoices)})')}")
    if not invoices:
        print("  No invoices.")
        return
    _print_detail_table([_row(inv, i) for i, inv in enumerate(invoices, 1)], INVOICE_COLUMNS)


# --- standalone `invoice` command -------------------------------------------

def _classify_invoice_input(raw: str) -> str:
    """'uid' for a Bubble _id, 'tkeg' for a numeric invoice-id, else 'invalid'."""
    s = raw.strip()
    if re.fullmatch(r"\d+x\d+", s):
        return "uid"
    if s.isdigit():
        return "tkeg"
    return "invalid"


def _lookup_invoice_by_id(value):
    print(f"  Looking up invoice by ID: {value} ...")
    try:
        inv = api_get(f"/api/1.1/obj/project:invoice/{value}").get("response", {})
    except Exception:
        inv = None
    if not inv or not inv.get("_id"):
        print(f"  No invoice found with ID '{value}'.", file=sys.stderr)
        return None
    return inv


def _lookup_invoice_by_tkeg_id(value):
    print(f"  Looking up invoice by invoice-id: {value} ...")
    try:
        rows = api_list("project:invoice", [
            {"key": "invoice-id", "constraint_type": "equals", "value": value},
        ])
    except Exception as e:
        print(f"  Lookup failed: {e}", file=sys.stderr)
        return None
    if not rows:
        print(f"  No invoice found with invoice-id '{value}'.", file=sys.stderr)
        return None
    if len(rows) > 1:
        print(f"  {DIM}Note: {len(rows)} invoices share this id; opening the first.{RESET}")
    return rows[0]


def cmd_invoice(args):
    if not args:
        print("Usage: invoice <invoice-id | _id>", file=sys.stderr)
        print("  invoice 1111111114                        open by invoice-id (TKEG id)", file=sys.stderr)
        print("  invoice 1777069193142x368449971970985500  open by its _id", file=sys.stderr)
        return
    raw = args[0].strip()
    kind = _classify_invoice_input(raw)
    if kind == "invalid":
        print(f"'{raw}' is not an invoice-id or an invoice _id.", file=sys.stderr)
        return
    inv = _lookup_invoice_by_id(raw) if kind == "uid" else _lookup_invoice_by_tkeg_id(raw)
    if inv:
        _render_invoice_detail(inv)


def _resolve_user_name(uid):
    if not uid:
        return "-"
    try:
        u = api_get(f"/api/1.1/obj/user/{uid}").get("response", {})
    except Exception:
        return str(uid)
    return u.get("user_name") or u.get("tkeg_user_id") or str(uid)


def _line_item_row(li, i, cur):
    from .entities import product_name
    return {
        "#": str(i),
        "Product": product_name(li.get("tkeg-expat-product")) if li.get("tkeg-expat-product") else str(li.get("product-id") or "-"),
        "Qty": str(li.get("quantity")) if li.get("quantity") is not None else "-",
        "Unit": _money(li.get("unit-amount"), cur),
        "Pre-Tax": _money(li.get("total-pre-tax-value"), cur),
        "Tax": _money(li.get("total-tax"), cur),
        "Total": _money(li.get("total-tax-inclusive-value"), cur),
    }


def _render_invoice_detail(inv):
    from .entities import entity_cell, project_label
    _reset_dots()
    cur = inv.get("invoice currency")

    label = inv.get("invoice-id") or inv.get("_id")
    print("\n" + _dot(f"Invoice {label}"))
    info = [
        ("Invoice ID", str(inv.get("invoice-id") or "-")),
        ("Status", inv.get("invoice-status") or "-"),
        ("Currency", cur or "-"),
        ("Pre-Tax", _money(inv.get("invoice-total-pre-tax-value"), cur)),
        ("Tax", _money(inv.get("invoice-total-tax-value"), cur)),
        ("Total", _money(inv.get("invoice-total-value-tax-included"), cur)),
        ("Issued", _date(inv.get("issuing date"))),
        ("Stripe Invoice ID", inv.get("stripe-invoice-id") or "-"),
        ("Belonging Project", project_label(inv.get("belonging projects new"))),
        ("TKEG Entity", entity_cell(inv.get("tkeg-expat-entity"), "entity:tkegexpat")),
        ("Issued By", _resolve_user_name(inv.get("tkeg expat portal user issued"))),
    ]
    _print_kv_table(info)

    print("\n  Fetching line items ...")
    try:
        items = api_list("invoice:lineitem", [
            {"key": "belonging invoice", "constraint_type": "equals", "value": inv["_id"]},
        ])
    except Exception:
        items = []
    print(f"\n{_dot(f'Line Items ({len(items)})')}")
    if not items:
        print("  No line items.")
    else:
        _print_detail_table([_line_item_row(li, i, cur) for i, li in enumerate(items, 1)], LINE_ITEM_COLUMNS)
    print()
