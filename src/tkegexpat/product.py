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

DISPLAY_FIELDS = [
    ("product-name-new2", "Product Name"),
    ("service_type", "Service Type"),
    ("corporate_price", "Price"),
    ("default_marking_currency", "Currency"),
    ("main_product", "Main Product"),
    ("tkeg_product_id (New)", "Product ID"),
    ("belonging_jurisdiction", "Belonging Jurisdiction"),
    ("full-applicable-jurisdictions", "Applicable Jurisdictions"),
    ("supply_info", "Supply"),
    ("Created Date", "Created"),
    ("Modified Date", "Modified"),
]

HIDDEN_FIELDS = {
    "Created By",
    "product_image",
    "TKEG Expat Ireland Stripe Price ID",
    "TKEG Expat US Stripe Price ID",
    "url_name",
    "Slug",
    "case-study-projects-items",
    "_id",
}


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


JURISDICTION_FIELDS = {"belonging_jurisdiction", "full-applicable-jurisdictions"}

SERVICE_TYPE_TO_CODE = {v: k.upper() for k, v in SERVICE_TYPES.items()}


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
    s = str(value)
    if len(s) > 22 and key in ("Created Date", "Modified Date"):
        return s[:10]
    return s


def _print_cards(products: List[dict], lang: str):
    if not products:
        print("No products found.")
        return

    known_keys = {f[0] for f in DISPLAY_FIELDS}

    for i, p in enumerate(products):
        if i > 0:
            print()
        name = _format_value("product-name-new2", p.get("product-name-new2"), lang)
        price = p.get("corporate_price", "-")
        currency = p.get("default_marking_currency", "")
        print(f"  {name}")
        print(f"  {currency} {price}")
        print("  " + "-" * 40)

        for field_key, label in DISPLAY_FIELDS:
            if field_key in ("product-name-new2", "corporate_price", "default_marking_currency"):
                continue
            val = _format_value(field_key, p.get(field_key), lang)
            print(f"  {label:<26} {val}")

        extra = [k for k in p if k not in known_keys and k not in HIDDEN_FIELDS]
        for k in extra:
            val = _format_value(k, p.get(k), lang)
            print(f"  {k:<26} {val}")


def _print_summary(products: List[dict], lang: str):
    if not products:
        print("No products found.")
        return

    name_w = max(len(_format_value("product-name-new2", p.get("product-name-new2"), lang)) for p in products)
    name_w = min(name_w, 45)

    header = f"  {'Product':<{name_w}}  {'Price':>8}  {'Main':>4}  {'Modified':<10}"
    print(header)
    print("  " + "-" * len(header.strip()))

    for p in products:
        name = _format_value("product-name-new2", p.get("product-name-new2"), lang)
        currency = p.get("default_marking_currency", "")
        price = f"{currency} {p.get('corporate_price', '-')}"
        main = "Yes" if p.get("main_product") else ""
        modified = str(p.get("Modified Date", ""))[:10]
        print(f"  {name:<{name_w}}  {price:>8}  {main:>4}  {modified:<10}")


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
    _print_cards(products, lang)
