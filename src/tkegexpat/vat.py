from __future__ import annotations

import sys

from .api import api_list
from .countries import lookup as country_lookup
from .cit import _dot, _reset_dots, _fmt, _print_detail_table, BOLD, DIM, RESET


def cmd_vat(args):
    if not args:
        print("Usage: vat <country>", file=sys.stderr)
        print("  e.g. vat us, vat gb, vat sg", file=sys.stderr)
        return

    from .config import effective_language
    lang = effective_language()

    abbr = args[0].upper()
    country = country_lookup(abbr)
    if not country:
        print(f"Unknown country code '{abbr}'.", file=sys.stderr)
        return

    cname = _fmt(country["name"], lang)
    print(f"  Fetching VAT rates for {cname} ({abbr}) ...")

    constraints = [
        {"key": "country_region", "constraint_type": "equals", "value": country["_id"]},
    ]
    rates = api_list("info:tax:vatrate", constraints)

    _reset_dots()

    if not rates:
        print(f"\n  No VAT rates found for {cname} ({abbr}).")
        return

    print(f"\n\n{_dot(f'{cname} ({abbr}) — VAT / Sales Tax Rates')}")

    rows = []
    for i, r in enumerate(rates, 1):
        rows.append({
            "#": str(i),
            "Name": _fmt(r.get("name-New2"), lang),
            "Type": r.get("tax_rate_type") or "-",
            "Rate": str(r.get("rate", "-")),
            "Active": "Yes" if r.get("active") else "No",
            "Description": _fmt(r.get("description-new2"), lang),
        })

    _print_detail_table(rows, ["#", "Name", "Type", "Rate", "Active", "Description"])
    print()
