from __future__ import annotations

import re
import sys

from .api import api_get, api_list
from .countries import id_to_abbr, lookup as country_lookup
from .cit import _dot, _reset_dots, _print_detail_table, _print_kv_table, DIM, RESET
from .product import SERVICE_TYPES, SERVICE_TYPE_TO_CODE, parse_code

_last_projects = []
_last_lang = "en_us"
_current_project_id = None  # the project whose detail is on screen (for the future `message` command)
# sub-tables of the project detail on screen, for view-project-item / view-invoice / view-contract
_detail_items = []
_detail_invoices = []
_detail_contracts = []

TABLE_COLUMNS = ["#", "Name", "Project ID", "Svc", "Country", "Value", "Progress"]


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _fmt_services(value):
    codes = [SERVICE_TYPE_TO_CODE.get(s, s) for s in _as_list(value)]
    return ", ".join(codes) if codes else "-"


def _fmt_countries(value):
    abbrs = [id_to_abbr(c) for c in _as_list(value)]
    return ", ".join(abbrs) if abbrs else "-"


def _fmt_value(total, currency):
    if isinstance(total, (int, float)):
        return f"{total:,.0f} {currency or ''}".strip()
    return "-"


def _fmt_progress(value):
    if isinstance(value, (int, float)):
        return f"{value:g}%"
    return "-"


def _fmt_date(value):
    if not value:
        return "-"
    s = str(value)
    return s.split("T")[0] if "T" in s else s


def _as_text(value):
    if value is None or value == "":
        return "-"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "-"
    return str(value)


def _project_row(p, i):
    return {
        "#": str(i),
        "Name": p.get("project_name") or "-",
        "Project ID": str(p.get("tkeg_project_id") or "-"),
        "Svc": _fmt_services(p.get("service_type")),
        "Country": _fmt_countries(p.get("country_region")),
        "Value": _fmt_value(p.get("total-value"), p.get("marking_currency")),
        "Progress": _fmt_progress(p.get("project_process")),
    }


def _print_projects(projects, header):
    _reset_dots()
    print(f"\n{_dot(header)}")
    rows = [_project_row(p, i) for i, p in enumerate(projects, 1)]
    _print_detail_table(rows, TABLE_COLUMNS)
    print(f"\n  {DIM}View full project: view <#>{RESET}\n")


def _classify_project_input(raw: str) -> str:
    """Classify a `project <arg>` first argument.

    - 'uid':  a Bubble record id, e.g. 1705400923505x291076600717843600
    - 'code': the <country><service> list form, e.g. usci (US + company-incorporation)
    - 'id':   otherwise, a numeric TKEG project id / Slug (they are identical), e.g. 4922376208

    Codes are alphabetic and TKEG project ids are numeric, so they never collide.
    """
    s = raw.strip()
    if re.fullmatch(r"\d+x\d+", s):
        return "uid"
    if "-" not in s and len(s) >= 4:
        service_code = s[-2:].lower()
        country_code = s[:-2]
        if SERVICE_TYPES.get(service_code) and country_lookup(country_code):
            return "code"
    return "id"


def _lookup_project_by_id(value: str):
    print(f"  Looking up project by ID: {value} ...")
    try:
        resp = api_get(f"/api/1.1/obj/projects:all/{value}")
        p = resp.get("response", resp)
    except Exception:
        p = None
    if not p or not p.get("_id"):
        print(f"  No project found with ID '{value}'.", file=sys.stderr)
        return None
    return p


def _lookup_project_by_tkeg_id(value: str):
    """Look up one project by its TKEG project id (which equals its Slug).

    Queries `tkeg_project_id` first (populated on every project); falls back to
    `Slug` for robustness.
    """
    print(f"  Looking up project by TKEG project id / slug: {value} ...")
    for key in ("tkeg_project_id", "Slug"):
        try:
            projects = api_list("projects:all", [
                {"key": key, "constraint_type": "equals", "value": value},
            ])
        except Exception as e:
            print(f"  Lookup failed: {e}", file=sys.stderr)
            return None
        if projects:
            if len(projects) > 1:
                print(f"  {DIM}Note: {len(projects)} projects share this id; opening the first.{RESET}")
            return projects[0]
    print(f"  No project found with TKEG project id / slug '{value}'.", file=sys.stderr)
    print(
        f"  {DIM}Tip: use a <country><service> code (e.g. 'project usci') to list, "
        f"or a project _id / TKEG project id to open one.{RESET}",
        file=sys.stderr,
    )
    return None


def cmd_project(args):
    global _last_projects, _last_lang
    _last_projects = []

    from .filters import parse_filters
    positional, extra, ok = parse_filters(args, crm_field="crm_entity", client_field="client_entity")
    if not ok:
        return

    if not positional:
        print("Usage: project <code | id | slug>  [--crm <_id>] [--client <_id|tkeg-id>]", file=sys.stderr)
        print("  project usci                              list US company-incorporation projects", file=sys.stderr)
        print("  project usci --crm <_id> --client <id>    filter that list by CRM / client", file=sys.stderr)
        print("  project 4922376208                        open one project by TKEG project id / slug", file=sys.stderr)
        print("  project 1705400923505x291076600717843600  open one project by its _id", file=sys.stderr)
        print(f"\nService type codes (for the <country><service> list form):", file=sys.stderr)
        for code, name in sorted(SERVICE_TYPES.items()):
            print(f"  {code}  {name}", file=sys.stderr)
        return

    from .config import effective_language
    _last_lang = effective_language()

    raw = positional[0].strip()
    kind = _classify_project_input(raw)

    if kind in ("uid", "id"):
        if extra:
            print(f"  {DIM}(--crm/--client ignored for direct lookup){RESET}")
        p = _lookup_project_by_id(raw) if kind == "uid" else _lookup_project_by_tkeg_id(raw)
        if not p:
            return
        _last_projects = [p]
        _print_projects([p], header=p.get("project_name") or f"Project {raw}")
        return True

    # code: <country><service> → list of matching projects
    country, service_type = parse_code(raw.lower())
    print(f"  Fetching projects: {country['abbr']} + {service_type} ...")
    constraints = [
        {"key": "country_region", "constraint_type": "contains", "value": country["_id"]},
        {"key": "service_type", "constraint_type": "contains", "value": service_type},
    ] + extra
    projects = api_list("projects:all", constraints)
    _last_projects = projects

    if not projects:
        print(f"\n  No projects found for {country['abbr']} + {service_type}.")
        return True

    _print_projects(projects, header=f"{country['abbr']} + {service_type} — Projects ({len(projects)})")
    return True


def cmd_view_project(args):
    if not _last_projects:
        print("No project list available. Run 'project <code|id>' first.", file=sys.stderr)
        return
    if not args:
        print("Usage: view <#>", file=sys.stderr)
        return
    try:
        idx = int(args[0])
    except ValueError:
        print(f"Invalid number: {args[0]}", file=sys.stderr)
        return
    if idx < 1 or idx > len(_last_projects):
        print(f"Invalid index. Choose 1-{len(_last_projects)}.", file=sys.stderr)
        return

    _render_project_detail(_last_projects[idx - 1])


def _render_project_detail(p):
    """Full project detail: basic info (entities resolved to prime name + UID)
    plus project items, invoices, and contracts. Messages are intentionally NOT
    shown here — the future `message` command surfaces them on demand."""
    global _current_project_id, _detail_items, _detail_invoices, _detail_contracts
    from .entities import entity_cell
    from . import project_item, invoice, contract, message

    pid = p["_id"]
    _current_project_id = pid
    message.set_context("project", pid, p.get("project_name") or "Project")

    print("\n  Loading project detail ...")
    # The project record has no end-date field; derive it from the latest item end date.
    items = project_item.fetch_for_project(pid)
    _detail_items = items
    end_date = project_item.latest_end_date(items)

    _reset_dots()
    print(f"\n{_dot(p.get('project_name') or 'Project')}")
    info = [
        ("Project Name", p.get("project_name") or "-"),
        ("TKEG Project ID", str(p.get("tkeg_project_id") or "-")),
        ("Project _id", pid),
        ("Service Type", _fmt_services(p.get("service_type"))),
        ("Country / Region", _fmt_countries(p.get("country_region"))),
        ("Status", _as_text(p.get("data: status (Selected)"))),
        ("Progress", _fmt_progress(p.get("project_process"))),
        ("Total Value", _fmt_value(p.get("total-value"), p.get("marking_currency"))),
        ("Profit (USD)", _fmt_value(p.get("profit USD"), "USD")),
        ("Start Date", _fmt_date(p.get("starting_date"))),
        ("End Date", _fmt_date(end_date)),
        ("Client Entity", entity_cell(p.get("client_entity"), "entity_client")),
        ("TKEG Entity", entity_cell(p.get("Entity: TKEG Expat"), "entity:tkegexpat")),
        ("CRM Entity", entity_cell(p.get("crm_entity"), "entity_crm")),
        ("Company Entity", entity_cell(p.get("comapny_entity"), "entity:company:all")),
    ]
    _print_kv_table(info)

    project_item.render_items(items)
    if items:
        print(f"  {DIM}Open an item: view-project-item <#>{RESET}")

    print("\n  Fetching invoices ...")
    _detail_invoices = invoice.fetch_for_project(pid)
    invoice.render_invoices(_detail_invoices)
    if _detail_invoices:
        print(f"  {DIM}Open an invoice: view-invoice <#>{RESET}")

    print("\n  Fetching contracts ...")
    _detail_contracts = contract.fetch_for_project(pid)
    contract.render_contracts(_detail_contracts)
    if _detail_contracts:
        print(f"  {DIM}Open a contract: view-contract <#>{RESET}")
    print(f"\n  {DIM}Project messages: message{RESET}\n")


def _view_from_detail(records, args, render, kind, cmd):
    if not records:
        print(f"No {kind} in the current project view. Open a project detail first.", file=sys.stderr)
        return
    if not args:
        print(f"Usage: {cmd} <#>", file=sys.stderr)
        return
    try:
        idx = int(args[0])
    except ValueError:
        print(f"Invalid number: {args[0]}", file=sys.stderr)
        return
    if idx < 1 or idx > len(records):
        print(f"Invalid index. Choose 1-{len(records)}.", file=sys.stderr)
        return
    render(records[idx - 1])


def cmd_view_item(args):
    from .project_item import _render_item_detail
    _view_from_detail(_detail_items, args, _render_item_detail, "project items", "view-project-item")


def cmd_view_invoice(args):
    from .invoice import _render_invoice_detail
    _view_from_detail(_detail_invoices, args, _render_invoice_detail, "invoices", "view-invoice")


def cmd_view_contract(args):
    from .contract import _render_contract_detail
    _view_from_detail(_detail_contracts, args, _render_contract_detail, "contracts", "view-contract")
