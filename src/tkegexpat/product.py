from __future__ import annotations

import sys
import textwrap
from typing import List, Optional

from .api import api_get, api_list
from .countries import id_to_abbr, lookup as country_lookup
from .i18n import extract_lang

SERVICE_TYPES = {
    "ci": "company-incorporation",
    "ba": "bank-account-opening",
    "ac": "accounting",
    "co": "consulting",
    "rm": "ready-made-company",
    "ra": "registered-address",
    "nd": "nominee-director",
    "cs": "company-secretary",
    "cd": "company-dissolution",
    "tr": "tax-registration",
    "sl": "special-license",
    "ar": "annual-return",
    "ca": "company-amendment",
    "af": "administration-fee",
    "os": "other-services",
}

NAME_MAX_WIDTH = 40

TABLE_COLUMNS = [
    ("_index", "#"),
    ("product-name-new2", "Name"),
    ("service_type", "Type"),
    ("_price_display", "Price"),
    ("main_product", "Main"),
    ("tkeg_product_id (New)", "PID"),
    ("full-applicable-jurisdictions", "Applicable"),
]

HIDDEN_FIELDS = {
    "Created By", "Created Date", "Modified Date",
    "product_image",
    "TKEG Expat Ireland Stripe Price ID",
    "TKEG Expat US Stripe Price ID",
    "url_name", "Slug",
    "case-study-projects-items", "_id",
    "supply_info", "belonging_jurisdiction",
    "corporate_price", "default_marking_currency",
}

JURISDICTION_FIELDS = {"belonging_jurisdiction", "full-applicable-jurisdictions"}
SERVICE_TYPE_TO_CODE = {v: k.upper() for k, v in SERVICE_TYPES.items()}

_last_products = []
_last_lang = "en_us"


def parse_code(code: str):
    if len(code) < 4:
        print(f"Invalid code '{code}'. Format: <country><service> e.g. usci, gbba", file=sys.stderr)
        print(f"\nService type codes: {', '.join(sorted(SERVICE_TYPES))}", file=sys.stderr)
        sys.exit(1)
    service_code = code[-2:]
    country_code = code[:-2]
    service_type = SERVICE_TYPES.get(service_code)
    if not service_type:
        print(f"Unknown service type code '{service_code}'.", file=sys.stderr)
        print(f"Valid codes: {', '.join(sorted(SERVICE_TYPES))}", file=sys.stderr)
        sys.exit(1)
    country = country_lookup(country_code)
    if not country:
        print(f"Unknown country code '{country_code.upper()}'.", file=sys.stderr)
        sys.exit(1)
    return country, service_type


def _format_value(key: str, value, lang: str) -> str:
    if value is None:
        return "-"
    if key == "service_type" and isinstance(value, str):
        return SERVICE_TYPE_TO_CODE.get(value, value)
    if key in JURISDICTION_FIELDS:
        if isinstance(value, list):
            return ", ".join(id_to_abbr(v) for v in value)
        return id_to_abbr(str(value))
    if key.lower().endswith("new2") or key.lower().endswith("-new2"):
        extracted = extract_lang(str(value), lang)
        if extracted:
            return extracted
    if isinstance(value, list):
        return str(len(value))
    if key == "main_product":
        return "Yes" if value else "No"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _print_table(products: List[dict], lang: str):
    if not products:
        print("No products found.")
        return

    rows = []
    for i, p in enumerate(products, 1):
        row = {}
        for key, label in TABLE_COLUMNS:
            if key == "_index":
                row[label] = str(i)
            elif key == "_price_display":
                cur = p.get("default_marking_currency", "")
                price = p.get("corporate_price", "-")
                row[label] = f"{cur} {price}"
            else:
                row[label] = _format_value(key, p.get(key), lang)
        rows.append(row)

    labels = [label for _, label in TABLE_COLUMNS]
    widths = {}
    for label in labels:
        w = max(len(label), *(len(r[label]) for r in rows))
        if label == "Name":
            w = min(w, NAME_MAX_WIDTH)
        widths[label] = w

    header = "  " + " | ".join(label.ljust(widths[label]) for label in labels)
    sep = "  " + "-+-".join("-" * widths[label] for label in labels)
    print(header)
    print(sep)

    for r in rows:
        name = r["Name"]
        if len(name) <= NAME_MAX_WIDTH:
            line = "  " + " | ".join(r[label].ljust(widths[label]) for label in labels)
            print(line)
        else:
            wrapped = textwrap.wrap(name, NAME_MAX_WIDTH)
            for li, part in enumerate(wrapped):
                if li == 0:
                    r_copy = dict(r)
                    r_copy["Name"] = part
                    line = "  " + " | ".join(r_copy[label].ljust(widths[label]) for label in labels)
                    print(line)
                else:
                    pad = "  " + " " * widths["#"] + " | "
                    print(pad + part)

    print(f"\n  Select a product for details: select <#>")


def _fetch_supply_detail(supply_id: str, lang: str):
    print(f"  Fetching supply details...")

    supply = api_get(f"/api/1.1/obj/supply_all/{supply_id}")
    s = supply.get("response", supply)

    name = _format_value("supply_product_name", s.get("supply_product_name"), lang)
    cur = s.get("marking_currency", "")
    cost = s.get("cost_price", "-")
    est_days = s.get("estimated-business-days", "-")
    est_gov = s.get("estimated-government-fee", "-")
    vat = s.get("vat", "-")
    memo = _format_value("public_memo_new2", s.get("public_memo_new2"), lang)
    internal = s.get("internal_memo", "")
    present = "Yes" if s.get("applicant must be present") else "No"

    print(f"\n  === Supply: {name} ===")
    print(f"  Cost Price             {cur} {cost}")
    print(f"  Est. Business Days     {est_days}")
    print(f"  Est. Government Fee    {est_gov}")
    print(f"  VAT                    {vat}")
    print(f"  Applicant Present      {present}")
    if memo and memo != "-":
        print(f"\n  Memo:")
        for line in textwrap.wrap(memo, 70):
            print(f"    {line}")
    if internal:
        print(f"\n  Internal Memo:")
        for line in textwrap.wrap(str(internal), 70):
            print(f"    {line}")

    included_ids = s.get("included services (new)", [])
    if included_ids:
        print(f"\n  --- Included Services ({len(included_ids)}) ---")
        for sid in included_ids:
            try:
                svc = api_get(f"/api/1.1/obj/supply_included_service/{sid}")
                sv = svc.get("response", svc)
                svc_name = _format_value("service-name_new2", sv.get("service-name_new2"), lang)
                qty = sv.get("quantity-included", "-")
                excluded = sv.get("not-included", False)
                status = "EXCLUDED" if excluded else f"x{qty}"
                print(f"    {status:<10} {svc_name}")
            except Exception:
                print(f"    {sid}")

    doc_ids = s.get("data: document requirements", [])
    if doc_ids:
        print(f"\n  --- Required Documents ({len(doc_ids)}) ---")
        for did in doc_ids:
            try:
                doc = api_get(f"/api/1.1/obj/supply_requirement_document/{did}")
                d = doc.get("response", doc)
                doc_memo = _format_value("memo-NEW2", d.get("memo-NEW2"), lang)
                doc_type = d.get("document_type", "-")
                entity = d.get("applicable_entity", "-")
                fmt = d.get("document_format", "")
                print(f"    [{entity}] {doc_type} ({fmt})")
                if doc_memo and doc_memo != "-":
                    for line in textwrap.wrap(doc_memo, 66):
                        print(f"      {line}")
            except Exception:
                print(f"    {did}")

    req_ids = s.get("data: requirements", [])
    if req_ids:
        print(f"\n  --- Requirements ({len(req_ids)}) ---")
        for rid in req_ids:
            try:
                req = api_get(f"/api/1.1/obj/supply_requirement/{rid}")
                r = req.get("response", req)
                req_name = _format_value("requirement_name-NEW2", r.get("requirement_name-NEW2"), lang)
                condition = _format_value("condition-NEW2", r.get("condition-NEW2"), lang)
                has_sol = "Yes" if r.get("has solution") else "No"
                included = r.get("item_included", 0)
                print(f"    {req_name}")
                if condition and condition != "-":
                    print(f"      Condition: {condition}")
                print(f"      Solution available: {has_sol}  |  Included: {included}")
            except Exception:
                print(f"    {rid}")


def cmd_select(args):
    global _last_products, _last_lang
    if not _last_products:
        print("No product list available. Run 'product <code>' first.", file=sys.stderr)
        return
    if not args:
        print("Usage: select <#>", file=sys.stderr)
        return

    try:
        idx = int(args[0])
    except ValueError:
        print(f"Invalid number: {args[0]}", file=sys.stderr)
        return

    if idx < 1 or idx > len(_last_products):
        print(f"Invalid index. Choose 1-{len(_last_products)}.", file=sys.stderr)
        return

    product = _last_products[idx - 1]
    lang = _last_lang

    name = _format_value("product-name-new2", product.get("product-name-new2"), lang)
    cur = product.get("default_marking_currency", "")
    price = product.get("corporate_price", "-")
    pid = product.get("tkeg_product_id (New)", "-")
    stype = _format_value("service_type", product.get("service_type"), lang)
    applicable = _format_value("full-applicable-jurisdictions", product.get("full-applicable-jurisdictions"), lang)

    print(f"\n  === Product #{idx}: {name} ===")
    print(f"  Price                  {cur} {price}")
    print(f"  Service Type           {stype}")
    print(f"  Product ID             {pid}")
    print(f"  Applicable             {applicable}")

    supply_id = product.get("supply_info")
    if supply_id:
        _fetch_supply_detail(supply_id, lang)
    else:
        print("\n  No supply linked to this product.")


def cmd_product(args):
    global _last_products, _last_lang
    if not args:
        print("Usage: product <code>", file=sys.stderr)
        print("  e.g. product usci  (US + company-incorporation)", file=sys.stderr)
        print(f"\nService type codes:", file=sys.stderr)
        for code, name in sorted(SERVICE_TYPES.items()):
            print(f"  {code}  {name}", file=sys.stderr)
        return

    from .config import load_settings
    lang = load_settings().get("language", "en_us")

    country, service_type = parse_code(args[0].lower())
    print(f"Fetching products: {country['abbr']} + {service_type} ...")

    constraints = [
        {"key": "full-applicable-jurisdictions", "constraint_type": "contains", "value": country["_id"]},
        {"key": "service_type", "constraint_type": "equals", "value": service_type},
    ]
    products = api_list("product:all", constraints)

    _last_products = products
    _last_lang = lang

    print(f"Found {len(products)} product(s).\n")
    _print_table(products, lang)
