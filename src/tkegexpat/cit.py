from __future__ import annotations

import sys

from .api import api_get
from .countries import lookup as country_lookup
from .i18n import display_width, extract_lang, ljust_cjk, strip_markup, wrap_cjk, wrap_display

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

_DOT_COLORS = [
    "\033[36m",  # cyan
    "\033[33m",  # yellow
    "\033[32m",  # green
    "\033[35m",  # magenta
    "\033[34m",  # blue
    "\033[31m",  # red
]
_dot_index = 0


def _dot(label: str) -> str:
    global _dot_index
    color = _DOT_COLORS[_dot_index % len(_DOT_COLORS)]
    _dot_index += 1
    return f"  {color}●{RESET} {BOLD}{label}{RESET}"


def _reset_dots():
    global _dot_index
    _dot_index = 0


def _print_kv_table(pairs: list, indent: int = 2):
    pad = " " * indent
    labels = ["Field", "Value"]
    key_w = max(display_width(k) for k, _ in pairs)
    val_w = max(display_width(v) for _, v in pairs)

    try:
        tw = __import__("os").get_terminal_size().columns
    except (ValueError, OSError):
        tw = 80
    available = tw - indent - 4
    key_w = min(key_w, 30)
    val_w = min(val_w, available - key_w)
    val_w = max(val_w, 20)

    header = pad + BOLD + ljust_cjk("Field", key_w) + f" {DIM}│{RESET}{BOLD} " + ljust_cjk("Value", val_w) + RESET
    sep = pad + DIM + "─" * key_w + "─┼─" + "─" * val_w + RESET
    print(header)
    print(sep)
    for k, v in pairs:
        wrapped = wrap_cjk(v, val_w)
        for li, line in enumerate(wrapped):
            label = k if li == 0 else ""
            print(pad + ljust_cjk(label, key_w) + f" {DIM}│{RESET} " + ljust_cjk(line, val_w))


MIN_COL_WIDTH = 6
DETAIL_COL_MAX = 40


def _term_width() -> int:
    try:
        import os
        return os.get_terminal_size().columns
    except (ValueError, OSError):
        return 80


def _fit_widths(widths: dict, labels: list, indent: int) -> dict:
    separators = 3 * (len(labels) - 1)
    available = _term_width() - indent - separators - 2
    if available < len(labels) * MIN_COL_WIDTH:
        available = len(labels) * MIN_COL_WIDTH
    fitted = {}
    for l in labels:
        fitted[l] = min(widths[l], DETAIL_COL_MAX)
    total = sum(fitted[l] for l in labels)
    if total <= available:
        remainder = available - total
        for l in labels:
            if remainder <= 0:
                break
            give = min(remainder, widths[l] - fitted[l])
            if give > 0:
                fitted[l] += give
                remainder -= give
        return fitted
    for l in labels:
        fitted[l] = max(MIN_COL_WIDTH, int(fitted[l] * available / total))
    overshoot = sum(fitted[l] for l in labels) - available
    if overshoot > 0:
        for l in sorted(labels, key=lambda l: fitted[l], reverse=True):
            if overshoot <= 0:
                break
            can = fitted[l] - MIN_COL_WIDTH
            if can > 0:
                take = min(overshoot, can)
                fitted[l] -= take
                overshoot -= take
    return fitted


def _print_detail_table(rows: list, labels: list, indent: int = 4, char_wrap=None):
    """char_wrap: labels whose cells use wrap_display, which never overflows
    (spaceless CJK, long URLs). Every other column keeps wrap_cjk."""
    if not rows:
        return
    pad = " " * indent
    char_wrap = set(char_wrap or ())
    widths = {}
    for l in labels:
        widths[l] = max(display_width(l), *(display_width(r.get(l, "-")) for r in rows))
    widths = _fit_widths(widths, labels, indent)

    header = pad + BOLD + f" {DIM}│{RESET}{BOLD} ".join(ljust_cjk(l, widths[l]) for l in labels) + RESET
    sep = pad + DIM + "─┼─".join("─" * widths[l] for l in labels) + RESET
    print(header)
    print(sep)
    for r in rows:
        wrapped = {}
        for l in labels:
            cell = r.get(l, "-") or "-"
            wrap = wrap_display if l in char_wrap else wrap_cjk
            wrapped[l] = wrap(cell, widths[l])
        max_lines = max(len(v) for v in wrapped.values())
        for li in range(max_lines):
            parts = []
            for l in labels:
                cell = wrapped[l]
                text = cell[li] if li < len(cell) else ""
                parts.append(ljust_cjk(text, widths[l]))
            print(pad + f" {DIM}│{RESET} ".join(parts))


def _fmt(value, lang) -> str:
    if value is None:
        return "-"
    s = str(value)
    if not s:
        return "-"
    if not lang:
        # Logged out → show the raw field, unfiltered by language.
        return strip_markup(s)
    extracted = extract_lang(s, lang)
    if extracted:
        return strip_markup(extracted)
    return strip_markup(s)


def cmd_cit(args):
    if not args:
        print("Usage: cit <country>", file=sys.stderr)
        print("  e.g. cit us, cit hk, cit sg", file=sys.stderr)
        return

    from .config import effective_language
    lang = effective_language()

    abbr = args[0].upper()
    country = country_lookup(abbr)
    if not country:
        print(f"Unknown country code '{abbr}'.", file=sys.stderr)
        return

    cname = _fmt(country["name"], lang)
    print(f"  Fetching CIT data for {cname} ({abbr}) ...")

    country_rec = api_get(f"/api/1.1/obj/info_country/{country['_id']}")
    c = country_rec.get("response", country_rec)

    tax_id = c.get("tax_info")
    if not tax_id:
        print(f"\n  No tax info linked for {cname}.")
        return

    tax_rec = api_get(f"/api/1.1/obj/info_tax/{tax_id}")
    t = tax_rec.get("response", tax_rec)

    _reset_dots()

    print(f"\n\n{_dot(f'{cname} ({abbr}) — Corporate Income Tax')}")
    summary = [
        ("CIT Rate", _fmt(t.get("general_cit_rate-NEW2"), lang)),
        ("General VAT Rate", _fmt(t.get("general_vat_rate"), lang)),
        ("Capital Gains Tax", _fmt(t.get("capital_gain_tax-NEW2"), lang)),
        ("CIT Estimate Payment Due", _fmt(t.get("cit_estimate_payment_due_date-NEW2"), lang)),
        ("CIT Payment Due", _fmt(t.get("cit_payment_due_date-NEW2"), lang)),
        ("CIT Return Due", _fmt(t.get("cit_return_due_date-NEW2"), lang)),
        ("WHT Resident (D/I/R)", _fmt(t.get("withdrawing_tax_resident （dividend / interest /royalty）"), lang)),
        ("WHT Non-Resident (D/I/R)", _fmt(t.get("withdrawing_tax_none_resident （dividend / interest /royalty）"), lang)),
        ("Effective Avg Tax Rate", _fmt(t.get("Composite Effective Average Tax Rate"), lang)),
        ("Effective Marginal Tax Rate", _fmt(t.get("Composite Effective Marginal Tax Rate"), lang)),
    ]
    _print_kv_table(summary)

    feature_ids = t.get("data: tax feature list") or []
    if feature_ids:
        print(f"\n{_dot(f'Tax Features ({len(feature_ids)})')}")
        feat_rows = []
        for i, fid in enumerate(feature_ids, 1):
            try:
                feat_rec = api_get(f"/api/1.1/obj/info_tax_feature/{fid}")
                fv = feat_rec.get("response", feat_rec)
                feat_rows.append({
                    "#": str(i),
                    "Header": _fmt(fv.get("header-new2"), lang),
                    "Detail": _fmt(fv.get("body-new2"), lang),
                })
            except Exception:
                feat_rows.append({"#": str(i), "Header": fid, "Detail": "-"})
        _print_detail_table(feat_rows, ["#", "Header", "Detail"])

    update_date = t.get("update date") or t.get("Modified Date") or "-"
    print(f"\n  {DIM}Last updated: {update_date}{RESET}\n")
