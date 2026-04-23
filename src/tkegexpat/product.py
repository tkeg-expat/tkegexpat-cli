from __future__ import annotations

import sys
from typing import List

from .api import api_list
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

TABLE_COLUMNS = [
    ("product-name-new2", "Name"),
    ("service_type", "Type"),
    ("corporate_price", "Price"),
    ("default_marking_currency", "Cur"),
    ("main_product", "Main"),
    ("tkeg_product_id (New)", "PID"),
    ("belonging_jurisdiction", "Jurisdiction"),
    ("full-applicable-jurisdictions", "Applicable"),
    ("supply_info", "Supply"),
]

HIDDEN_FIELDS = {
    "Created By", "Created Date", "Modified Date",
    "product_image",
    "TKEG Expat Ireland Stripe Price ID",
    "TKEG Expat US Stripe Price ID",
    "url_name", "Slug",
    "case-study-projects-items", "_id",
}

JURISDICTION_FIELDS = {"belonging_jurisdiction", "full-applicable-jurisdictions"}
SERVICE_TYPE_TO_CODE = {v: k.upper() for k, v in SERVICE_TYPES.items()}


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
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _print_table(products: List[dict], lang: str):
    if not products:
        print("No products found.")
        return

    rows = []
    for p in products:
        row = {}
        for key, label in TABLE_COLUMNS:
            row[label] = _format_value(key, p.get(key), lang)
        rows.append(row)

    labels = [label for _, label in TABLE_COLUMNS]
    widths = {}
    for label in labels:
        widths[label] = max(len(label), *(len(r[label]) for r in rows))

    header = "  " + " | ".join(label.ljust(widths[label]) for label in labels)
    sep = "  " + "-+-".join("-" * widths[label] for label in labels)
    print(header)
    print(sep)
    for r in rows:
        line = "  " + " | ".join(r[label].ljust(widths[label]) for label in labels)
        print(line)


def cmd_product(args):
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
    print(f"Found {len(products)} product(s).\n")
    _print_table(products, lang)
