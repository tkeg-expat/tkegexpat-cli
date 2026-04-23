from __future__ import annotations

import re
import sys
from typing import List

from .api import api_list
from .countries import lookup as country_lookup
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

NEW2_FIELDS = {"product-name-new2"}


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
        return ""
    if key.lower().endswith("new2") or key.lower().endswith("-new2"):
        extracted = extract_lang(str(value), lang)
        if extracted:
            return extracted
    if isinstance(value, list):
        return f"[{len(value)} items]"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    s = str(value)
    if len(s) > 60:
        return s[:57] + "..."
    return s


def _print_table(products: List[dict], lang: str):
    if not products:
        print("No products found.")
        return

    skip = {"_id"}
    keys = []
    for k in products[0]:
        if k not in skip:
            keys.append(k)

    rows = []
    for p in products:
        row = {"_id": p.get("_id", "")[:16] + "..."}
        for k in keys:
            row[k] = _format_value(k, p.get(k), lang)
        rows.append(row)

    all_keys = ["_id"] + keys
    widths = {}
    for k in all_keys:
        widths[k] = max(len(k), *(len(r.get(k, "")) for r in rows))
        widths[k] = min(widths[k], 40)

    header = " | ".join(k.ljust(widths[k])[:widths[k]] for k in all_keys)
    sep = "-+-".join("-" * widths[k] for k in all_keys)
    print(header)
    print(sep)
    for r in rows:
        line = " | ".join(r.get(k, "").ljust(widths[k])[:widths[k]] for k in all_keys)
        print(line)


def cmd_product(args):
    if not args:
        print("Usage: tkegexpat product <code>", file=sys.stderr)
        print("  e.g. tkegexpat product usci  (US + company-incorporation)", file=sys.stderr)
        print(f"\nService type codes:", file=sys.stderr)
        for code, name in sorted(SERVICE_TYPES.items()):
            print(f"  {code}  {name}", file=sys.stderr)
        sys.exit(1)

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
