from __future__ import annotations

import sys

from .api import api_list
from .countries import lookup as country_lookup
from .cit import _dot, _reset_dots, _fmt, _print_detail_table, _print_kv_table, BOLD, DIM, RESET

_last_entities = []
_last_lang = "en_us"

POSITIVE_VALUES = {"POSITIVE", "Yes", "TRUE", "true"}
NEGATIVE_VALUES = {"NEGATIVE", "No", "FALSE", "false"}

TABLE_COLUMNS = ["#", "Abbr", "Full Name", "Liability", "Capital Mkt"]


def _yn(value) -> str:
    if not value:
        return "-"
    s = str(value)
    if s in POSITIVE_VALUES:
        return "Yes"
    if s in NEGATIVE_VALUES:
        return "No"
    return s


def cmd_legal_entity(args):
    global _last_entities, _last_lang
    _last_entities = []

    if not args:
        print("Usage: legal-entity <country>", file=sys.stderr)
        print("  e.g. legal-entity us, legal-entity hk", file=sys.stderr)
        return

    from .config import load_settings
    lang = load_settings().get("language", "en_us")
    _last_lang = lang

    abbr = args[0].upper()
    country = country_lookup(abbr)
    if not country:
        print(f"Unknown country code '{abbr}'.", file=sys.stderr)
        return

    cname = _fmt(country["name"], lang)
    print(f"  Fetching legal entities for {cname} ({abbr}) ...")

    constraints = [
        {"key": "country_region", "constraint_type": "equals", "value": country["_id"]},
    ]
    entities = api_list("info_company_type", constraints)
    _last_entities = entities

    _reset_dots()

    if not entities:
        print(f"\n  No legal entity types found for {cname} ({abbr}).")
        return

    print(f"\n{_dot(f'{cname} ({abbr}) — Legal Entity Types ({len(entities)})')}")

    rows = []
    for i, e in enumerate(entities, 1):
        rows.append({
            "#": str(i),
            "Abbr": e.get("legal_entity_ abbreviation") or "-",
            "Full Name": e.get("legal_entity_full_name") or "-",
            "Liability": _yn(e.get("limited_liability")),
            "Capital Mkt": _yn(e.get("publicly_participates_in_capital_market")),
        })

    _print_detail_table(rows, TABLE_COLUMNS)
    print(f"\n  {DIM}View details: view <#>{RESET}\n")
    return True


def cmd_view_entity(args):
    global _last_entities, _last_lang
    if not _last_entities:
        print("No legal entity list available. Run 'legal-entity <country>' first.", file=sys.stderr)
        return
    if not args:
        print("Usage: view <#>", file=sys.stderr)
        return

    try:
        idx = int(args[0])
    except ValueError:
        print(f"Invalid number: {args[0]}", file=sys.stderr)
        return

    if idx < 1 or idx > len(_last_entities):
        print(f"Invalid index. Choose 1-{len(_last_entities)}.", file=sys.stderr)
        return

    lang = _last_lang
    e = _last_entities[idx - 1]

    _reset_dots()

    name = e.get("legal_entity_full_name") or "-"
    abbr = e.get("legal_entity_ abbreviation") or "-"
    print(f"\n\n{_dot(f'#{idx}: {name} ({abbr})')}")

    info = [
        ("Full Name", name),
        ("Abbreviation", abbr),
        ("Limited Liability", _yn(e.get("limited_liability"))),
        ("Ownership", e.get("ownership") or "-"),
        ("Capital Market", _yn(e.get("publicly_participates_in_capital_market"))),
        ("Local Director Not Required", _yn(e.get("local_director_not_mandatory"))),
        ("Local Secretary Not Required", _yn(e.get("local_secretary_not_mandatory"))),
        ("Legal Rep Not Required", _yn(e.get("legal_representative_not_mandatory"))),
        ("Capital Injection Not Required", _yn(e.get("capital_injection_not_mandatory"))),
        ("Min Registered Capital", _fmt(e.get("minimum_registered_capital-NEW2"), lang)),
        ("Capital Injection Reqs", _fmt(e.get("requirements_for_capital_injection-NEW2"), lang)),
        ("Director Reqs", _fmt(e.get("requirements_for_directors-NEW2"), lang)),
        ("Shareholder Reqs", _fmt(e.get("requirements_for_shareholders-NEW2"), lang)),
    ]
    _print_kv_table(info)

    memo = _fmt(e.get("memo_new2"), lang)
    if memo and memo != "-":
        print(f"\n{_dot('Memo')}")
        for line in memo.split("\n"):
            print(f"  {line}")

    quick_view = _fmt(e.get("quick_view_NEW2"), lang)
    if quick_view and quick_view != "-":
        print(f"\n{_dot('Quick View')}")
        for line in quick_view.split("\n"):
            print(f"  {line}")

    ref = (e.get("references") or "").strip()
    if ref:
        print(f"\n  {DIM}Ref: {ref}{RESET}")

    print()
