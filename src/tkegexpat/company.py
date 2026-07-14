from __future__ import annotations

import re
import sys

from .api import api_get, api_list
from .countries import id_to_abbr, lookup as country_lookup
from .cit import _dot, _reset_dots, _fmt, _print_detail_table, _print_kv_table, BOLD, DIM, RESET

_last_companies = []
_last_dues = []
_last_lang = "en_us"

TABLE_COLUMNS = ["#", "Name", "SIN", "ID", "Status", "Reg Date", "Tax ID"]


def _format_date(value):
    if not value:
        return "-"
    s = str(value)
    if "T" in s:
        return s.split("T")[0]
    return s


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


def _print_additional_info(text):
    from .i18n import strip_markup

    lines = strip_markup(text).strip().split("\n")
    sections = []
    current_name = None
    current_lines = []

    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("======"):
            continue
        if stripped.endswith(":") and ":" not in stripped[:-1] and len(stripped) > 1:
            if current_name is not None or current_lines:
                sections.append((current_name or "General", "\n".join(current_lines)))
                current_lines = []
            current_name = stripped[:-1]
            continue
        current_lines.append(stripped)

    if current_name is not None or current_lines:
        sections.append((current_name or "General", "\n".join(current_lines)))

    if sections:
        _print_kv_table([(name, body or "-") for name, body in sections])


def _classify_company_input(raw: str) -> str:
    """Classify a `company <arg>` first argument.

    - 'uid':      a Bubble record id, e.g. 1754212519690x256973978537820160
    - 'country':  a country code that resolves (us, hk, gb) -> country list form
    - 'tkeg_id':  otherwise, a TKEG company id (e.g. 1111111176) -> direct lookup

    A country code always wins the list interpretation, so the existing
    `company us [status]` behaviour is preserved. TKEG company ids are numeric
    and never collide with the alphabetic country codes.
    """
    s = raw.strip()
    if re.fullmatch(r"\d+x\d+", s):
        return "uid"
    if country_lookup(s.upper()):
        return "country"
    return "tkeg_id"


def _lookup_company_by_id(value: str):
    """Fetch one company by its Bubble _id, or None if not found."""
    print(f"  Looking up company by ID: {value} ...")
    try:
        resp = api_get(f"/api/1.1/obj/entity:company:all/{value}")
        c = resp.get("response", resp)
    except Exception:
        c = None
    if not c or not c.get("_id"):
        print(f"  No company found with ID '{value}'.", file=sys.stderr)
        return None
    return c


def _lookup_company_by_tkeg_id(value: str):
    """Fetch one company by its tkeg_company_id, or None if not found."""
    print(f"  Looking up company by TKEG company ID: {value} ...")
    try:
        companies = api_list("entity:company:all", [
            {"key": "tkeg_company_id", "constraint_type": "equals", "value": value},
        ])
    except Exception as e:
        print(f"  Lookup failed: {e}", file=sys.stderr)
        return None
    if not companies:
        print(f"  No company found with TKEG company ID '{value}'.", file=sys.stderr)
        print(
            f"  {DIM}Tip: pass a country code (e.g. 'company us') to list a country's "
            f"companies, or a company _id / TKEG company id to open one.{RESET}",
            file=sys.stderr,
        )
        return None
    if len(companies) > 1:
        print(f"  {DIM}Note: {len(companies)} companies share this id; opening the first.{RESET}")
    return companies[0]


def cmd_company(args):
    global _last_companies, _last_lang
    _last_companies = []

    from .filters import parse_filters
    positional, extra, ok = parse_filters(args, crm_field="data: crm-entity", client_field="client_entity")
    if not ok:
        return

    if not positional:
        print("Usage: company <country|id> [status]  [--crm <_id>] [--client <_id|tkeg-id>]", file=sys.stderr)
        print("  company us                                list US managed companies", file=sys.stderr)
        print("  company hk live --crm <_id>               list HK 'live' companies for a CRM", file=sys.stderr)
        print("  company 1111111176                        open one company by its TKEG company id", file=sys.stderr)
        print("  company 1754212519690x256973978537820160  open one company by its _id", file=sys.stderr)
        return

    from .config import effective_language
    lang = effective_language()
    _last_lang = lang

    raw = positional[0].strip()
    kind = _classify_company_input(raw)

    if kind in ("uid", "tkeg_id"):
        if extra:
            print(f"  {DIM}(--crm/--client ignored for direct lookup){RESET}")
        c = _lookup_company_by_id(raw) if kind == "uid" else _lookup_company_by_tkeg_id(raw)
        if not c:
            return
        _last_companies = [c]
        _render_company_detail(c, lang)
        return True

    # country list form: company <country> [status]
    abbr = raw.upper()
    country = country_lookup(abbr)
    if not country:
        print(f"Unknown country code '{abbr}'.", file=sys.stderr)
        return

    cname = _fmt(country["name"], lang)

    constraints = [
        {"key": "data-jurisdiction", "constraint_type": "equals", "value": country["_id"]},
    ] + extra

    status_filter = None
    if len(positional) > 1:
        status_filter = " ".join(positional[1:]).lower()

    label = f"{cname} ({abbr})"
    if status_filter:
        label += f" — {status_filter}"
    print(f"  Fetching companies: {label} ...")

    companies = api_list("entity:company:all", constraints)

    if status_filter:
        companies = [
            c for c in companies
            if (c.get("comapny_registration_and_annual_return") or "").lower() == status_filter
        ]

    _last_companies = companies

    if not companies:
        print(f"\n  No companies found for {label}.")
        return

    _reset_dots()

    print(f"  Resolving names ...")
    rows = []
    for i, c in enumerate(companies, 1):
        prime = _resolve_prime(c.get("prime entity"))
        rows.append({
            "#": str(i),
            "Name": prime.get("entity_name") or "-",
            "SIN": prime.get("social_identification_number") or "-",
            "ID": c.get("tkeg_company_id") or "-",
            "Status": c.get("comapny_registration_and_annual_return") or "-",
            "Reg Date": _format_date(c.get("registration_date")),
            "Tax ID": c.get("tax_id") or "-",
        })

    print(f"\n{_dot(f'{label} — Managed Companies ({len(companies)})')}")
    _print_detail_table(rows, TABLE_COLUMNS)
    print(f"\n  {DIM}View company details: view <#>{RESET}\n")
    return True


def cmd_view_company(args):
    if not _last_companies:
        print("No company list available. Run 'company <country> [status]' first.", file=sys.stderr)
        return
    if not args:
        print("Usage: view <#>", file=sys.stderr)
        return

    try:
        idx = int(args[0])
    except ValueError:
        print(f"Invalid number: {args[0]}", file=sys.stderr)
        return

    if idx < 1 or idx > len(_last_companies):
        print(f"Invalid index. Choose 1-{len(_last_companies)}.", file=sys.stderr)
        return

    _render_company_detail(_last_companies[idx - 1], _last_lang, idx)


def _render_company_detail(c, lang, idx=None):
    """Render the full company detail view for one company record.

    Shared by `view <#>` (from a list) and the direct `company <id>` lookup.
    ``idx`` is the 1-based list position for the heading, or None for a
    directly-resolved company.
    """
    global _last_dues

    company_id = c["_id"]

    _reset_dots()

    prime = _resolve_prime(c.get("prime entity"))
    prime_name = prime.get("entity_name") or "-"

    heading = f"#{idx}: {prime_name}" if idx else prime_name
    print(f"\n\n{_dot(heading)}")

    info = [
        ("Company ID", c.get("tkeg_company_id") or "-"),
        ("Status", c.get("comapny_registration_and_annual_return") or "-"),
        ("Registration Date", _format_date(c.get("registration_date"))),
        ("Tax ID", c.get("tax_id") or "-"),
        ("Tax ID Status", c.get("tax_id_status") or "-"),
        ("Tax ID Reg Date", _format_date(c.get("tax_id_registration_date"))),
        ("Jurisdiction", id_to_abbr(c.get("data-jurisdiction") or "")),
        ("Contact Email", c.get("tkeg: to-email") or "-"),
        ("Entity Name", prime.get("entity_name") or "-"),
        ("Entity Type", prime.get("entity_type") or "-"),
        ("Entity ID", prime.get("tkeg_entity_id") or "-"),
        ("SIN", prime.get("social_identification_number") or "-"),
        ("Email", prime.get("email") or "-"),
        ("Phone", prime.get("phone_numer") or "-"),
        ("Contact Person", prime.get("person_of_contact_name") or "-"),
        ("Address", _format_address(prime.get("entity_address"))),
    ]
    _print_kv_table(info)

    memo_id = c.get("new: additional information")
    if memo_id:
        try:
            msg = api_get(f"/api/1.1/obj/message:project+company+todo/{memo_id}")
            m = msg.get("response", msg)
            body = (m.get("message") or "").strip()
            if body:
                print(f"\n{_dot('Additional Information')}")
                _print_additional_info(body)
        except Exception:
            pass

    global _last_dues
    _last_dues = []

    print(f"\n  Fetching due dates ...")
    due_constraints = [
        {"key": "company-element", "constraint_type": "equals", "value": company_id},
    ]
    dues = api_list("company:due-dates", due_constraints)

    if not dues:
        print(f"\n{_dot('Due Dates')}")
        print(f"  No due dates found.")
    else:
        dues.sort(key=lambda d: d.get("next_due_date") or "")
        _last_dues = dues
        print(f"\n{_dot(f'Due Dates ({len(dues)})')}")
        due_rows = []
        for i, d in enumerate(dues, 1):
            product_id = d.get("product-element")
            product_name = "-"
            if product_id:
                try:
                    from .i18n import extract_lang, strip_markup
                    prec = api_get(f"/api/1.1/obj/product:all/{product_id}")
                    p = prec.get("response", prec)
                    raw = p.get("product-name-new2") or ""
                    if not lang:
                        product_name = strip_markup(raw) if raw else "-"
                    else:
                        extracted = extract_lang(raw, lang)
                        product_name = strip_markup(extracted) if extracted else raw or "-"
                except Exception:
                    product_name = product_id[:12]
            due_rows.append({
                "#": str(i),
                "Name": d.get("management_name") or "-",
                "Product": product_name,
                "Service": d.get("management_service_type") or "-",
                "Status": d.get("management_status") or "-",
                "Due Date": _format_date(d.get("next_due_date")),
                "Memo": d.get("memo") or "-",
            })
        _print_detail_table(due_rows, ["#", "Name", "Product", "Service", "Status", "Due Date", "Memo"])
        print(f"\n  {DIM}View due date product: view-product <#>{RESET}")

    from . import message
    message.set_context("company", company_id, prime_name)
    print(f"\n  {DIM}Company messages: message{RESET}")
    print()


def cmd_view_product(args):
    if not _last_dues:
        print("No due dates available. Run 'view <#>' on a company first.", file=sys.stderr)
        return
    if not args:
        print("Usage: due <#>", file=sys.stderr)
        return

    try:
        idx = int(args[0])
    except ValueError:
        print(f"Invalid number: {args[0]}", file=sys.stderr)
        return

    if idx < 1 or idx > len(_last_dues):
        print(f"Invalid index. Choose 1-{len(_last_dues)}.", file=sys.stderr)
        return

    d = _last_dues[idx - 1]
    product_id = d.get("product-element")
    if not product_id:
        print(f"  Due date #{idx} has no linked product.", file=sys.stderr)
        return

    print(f"  Fetching product ...")
    try:
        rec = api_get(f"/api/1.1/obj/product:all/{product_id}")
        product = rec.get("response", rec)
    except Exception as e:
        print(f"  Failed to fetch product: {e}", file=sys.stderr)
        return

    from . import product as product_mod
    product_mod._last_products = [product]
    product_mod._last_lang = _last_lang
    product_mod._last_requirements = []
    product_mod._last_view_product = None
    product_mod.cmd_view_more(["1"])
