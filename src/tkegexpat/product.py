from __future__ import annotations

import os
import sys
from typing import List, Optional

from .api import api_get, api_list
from .countries import id_to_abbr, lookup as country_lookup
from .i18n import display_width, extract_lang, ljust_cjk, strip_markup, wrap_cjk

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
DETAIL_COL_MAX = 40

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

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
MIN_COL_WIDTH = 6

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

_last_products = []
_last_lang = "en_us"
_last_view_product = None
_last_requirements = []
_last_search_country_id = None
_last_search_country_abbr = None


def _as_list(value) -> list:
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _term_width() -> int:
    try:
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
        shrinkable = sorted(labels, key=lambda l: fitted[l], reverse=True)
        for l in shrinkable:
            if overshoot <= 0:
                break
            can = fitted[l] - MIN_COL_WIDTH
            if can <= 0:
                continue
            take = min(overshoot, can)
            fitted[l] -= take
            overshoot -= take
    remainder = available - sum(fitted[l] for l in labels)
    for l in labels:
        if remainder <= 0:
            break
        fitted[l] += 1
        remainder -= 1
    return fitted


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
            return strip_markup(extracted)
    if isinstance(value, list):
        return str(len(value))
    if key == "main_product":
        return "Yes" if value else "No"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return strip_markup(str(value))


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
        w = max(display_width(label), *(display_width(r[label]) for r in rows))
        widths[label] = w
    widths = _fit_widths(widths, labels, indent=2)

    header = f"  {BOLD}" + f" {DIM}│{RESET}{BOLD} ".join(ljust_cjk(label, widths[label]) for label in labels) + RESET
    sep = f"  {DIM}" + "─┼─".join("─" * widths[label] for label in labels) + RESET
    print(header)
    print(sep)

    for r in rows:
        wrapped = {l: wrap_cjk(r[l], widths[l]) for l in labels}
        max_lines = max(len(v) for v in wrapped.values())
        for li in range(max_lines):
            parts = []
            for l in labels:
                cell = wrapped[l]
                text = cell[li] if li < len(cell) else ""
                parts.append(ljust_cjk(text, widths[l]))
            print("  " + f" {DIM}│{RESET} ".join(parts))

    print(f"\n  {DIM}View product details: view <#>{RESET}")


def _print_detail_table(rows: List[dict], labels: List[str], indent: int = 4,
                        span_rows: Optional[List[dict]] = None):
    if not rows and not span_rows:
        return
    pad = " " * indent
    all_rows = rows or []
    widths = {}
    for l in labels:
        w = max(display_width(l), *(display_width(r.get(l, "-")) for r in all_rows)) if all_rows else display_width(l)
        widths[l] = w
    widths = _fit_widths(widths, labels, indent)
    total_width = sum(widths[l] for l in labels) + 3 * (len(labels) - 1)

    header = pad + BOLD + f" {DIM}│{RESET}{BOLD} ".join(ljust_cjk(l, widths[l]) for l in labels) + RESET
    sep = pad + DIM + "─┼─".join("─" * widths[l] for l in labels) + RESET
    print(header)
    print(sep)

    span_map = {}
    if span_rows:
        for sr in span_rows:
            span_map.setdefault(sr["_before"], []).append(sr["_text"])

    for ri, r in enumerate(all_rows):
        for span_text in span_map.get(ri, []):
            if ri > 0:
                print()
            print(pad + BOLD + ljust_cjk(span_text, total_width) + RESET)
            print(sep)
        wrapped = {l: wrap_cjk(r.get(l, "-") or "-", widths[l]) for l in labels}
        max_lines = max(len(v) for v in wrapped.values())
        for li in range(max_lines):
            parts = []
            for l in labels:
                cell_lines = wrapped[l]
                text = cell_lines[li] if li < len(cell_lines) else ""
                parts.append(ljust_cjk(text, widths[l]))
            print(pad + f" {DIM}│{RESET} ".join(parts))


def _print_kv_table(pairs: List[tuple], indent: int = 2):
    pad = " " * indent
    labels = ["Field", "Value"]
    key_w = max(display_width(k) for k, _ in pairs)
    val_w = max(display_width(v) for _, v in pairs)
    widths = {"Field": key_w, "Value": val_w}
    widths = _fit_widths(widths, labels, indent)
    key_w = widths["Field"]
    val_w = widths["Value"]
    header = pad + BOLD + ljust_cjk("Field", key_w) + f" {DIM}│{RESET}{BOLD} " + ljust_cjk("Value", val_w) + RESET
    sep = pad + DIM + "─" * key_w + "─┼─" + "─" * val_w + RESET
    print(header)
    print(sep)
    for k, v in pairs:
        wrapped = wrap_cjk(v, val_w)
        for li, line in enumerate(wrapped):
            label = k if li == 0 else ""
            print(pad + ljust_cjk(label, key_w) + f" {DIM}│{RESET} " + ljust_cjk(line, val_w))


def _resolve_supplier_name(supplier_id: str) -> str:
    try:
        supplier = api_get(f"/api/1.1/obj/entity_supplier/{supplier_id}")
        sv = supplier.get("response", supplier)
        prime_id = sv.get("prime_entity")
        if prime_id:
            prime = api_get(f"/api/1.1/obj/entity:prime/{prime_id}")
            pv = prime.get("response", prime)
            return pv.get("entity_name", supplier_id)
    except Exception:
        pass
    return supplier_id


def _resolve_supply_name(supply_id: str, lang: str) -> str:
    try:
        supply = api_get(f"/api/1.1/obj/supply_all/{supply_id}")
        sv = supply.get("response", supply)
        return sv.get("supply_product_name", supply_id)
    except Exception:
        return supply_id


def _product_label(product: dict, lang: str) -> str:
    raw = product.get("product-name-new2") or product.get("url_name") or "-"
    return _format_value("product-name-new2", raw, lang)


def _print_resolving_products(products: List[dict], lang: str):
    if not products:
        print(f"    {DIM}No TKEG product found.{RESET}")
        return

    print(f"    Found {len(products)} resolving product(s):")
    for i, product in enumerate(products, 1):
        name = _product_label(product, lang)
        cur = product.get("default_marking_currency", "")
        price = product.get("corporate_price", "-")
        main = "main" if product.get("main_product") else "variant"
        print(f"      {i}. {name}  {DIM}({cur} {price}, {main}){RESET}")


def _print_faqs(faq_rows: List[dict]):
    if not faq_rows:
        print(f"  {DIM}No FAQs linked to this product's supply.{RESET}")
        return

    print(f"\n{_dot(f'FAQs ({len(faq_rows)})')}")
    _print_detail_table(faq_rows, ["#", "Question", "Answer"], indent=4)


def cmd_view_more(args):
    global _last_products, _last_lang, _last_view_product, _last_requirements
    _last_view_product = None
    _last_requirements = []
    if not _last_products:
        print("No product list available. Run 'product <code>' first.", file=sys.stderr)
        return
    if not args:
        print("Usage: view <#>", file=sys.stderr)
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
    _last_view_product = product
    lang = _last_lang

    name = _format_value("product-name-new2", product.get("product-name-new2"), lang)
    pid = product.get("tkeg_product_id (New)", "-")
    stype = _format_value("service_type", product.get("service_type"), lang)
    main = _format_value("main_product", product.get("main_product"), lang)
    cur = product.get("default_marking_currency", "")
    price = product.get("corporate_price", "-")
    applicable = _format_value("full-applicable-jurisdictions", product.get("full-applicable-jurisdictions"), lang)

    supply_id = product.get("supply_info")
    _reset_dots()
    if not supply_id:
        print(f"\n{_dot(f'#{idx}: {name}')}")
        info = [
            ("Product ID", pid), ("Service Type", stype), ("Main Product", main),
            ("Price", f"{cur} {price}"), ("Applicable", applicable),
        ]
        _print_kv_table(info)
        print("\n  No supply linked to this product.")
        return

    print("  Fetching details...")
    supply = api_get(f"/api/1.1/obj/supply_all/{supply_id}")
    s = supply.get("response", supply)

    s_cur = s.get("marking_currency", "")
    cost = s.get("cost_price", "-")
    est_days = s.get("estimated-business-days", "-")
    est_gov = s.get("estimated-government-fee", "-")
    vat = s.get("vat", "-")
    memo = _format_value("public_memo_new2", s.get("public_memo_new2"), lang)
    internal = strip_markup(s.get("internal_memo", "") or "")
    present = "Yes" if s.get("applicant must be present") else "No"

    print(f"\n\n{_dot(f'#{idx}: {name}')}")
    info = [
        ("Product ID", pid), ("Service Type", stype), ("Main Product", main),
        ("Price", f"{cur} {price}"), ("Applicable", applicable),
        ("Cost Price", f"{s_cur} {cost}"),
        ("Est. Business Days", str(est_days)), ("Est. Government Fee", str(est_gov)),
        ("VAT", str(vat)), ("Applicant Present", present),
    ]
    _print_kv_table(info)
    print()

    if (memo and memo != "-") or internal:
        print(f"\n{_dot('Memos')}")
        memo_pairs = []
        if memo and memo != "-":
            memo_pairs.append(("Public", memo))
        if internal:
            memo_pairs.append(("Internal", internal))
        _print_kv_table(memo_pairs)
        print()

    included_ids = s.get("included services (new)", [])
    if included_ids:
        print(f"\n{_dot(f'Included Services ({len(included_ids)})')}")
        inc_rows = []
        for sid in included_ids:
            try:
                svc = api_get(f"/api/1.1/obj/supply_included_service/{sid}")
                sv = svc.get("response", svc)
                svc_name = _format_value("service-name_new2", sv.get("service-name_new2"), lang)
                qty = sv.get("quantity-included", "-")
                excluded = sv.get("not-included", False)
                inc_rows.append({
                    "Service": svc_name,
                    "Qty": str(qty),
                    "Status": "EXCLUDED" if excluded else "Included",
                })
            except Exception:
                inc_rows.append({"Service": sid, "Qty": "-", "Status": "-"})
        _print_detail_table(inc_rows, ["Service", "Qty", "Status"])
        print()

    doc_ids = s.get("data: document requirements", [])
    if doc_ids:
        print(f"\n{_dot(f'Required Documents ({len(doc_ids)})')}")
        docs_by_entity = {}
        doc_order = []
        for did in doc_ids:
            try:
                doc = api_get(f"/api/1.1/obj/supply_requirement_document/{did}")
                d = doc.get("response", doc)
                entity = d.get("applicable_entity", "-")
                if entity not in docs_by_entity:
                    doc_order.append(entity)
                docs_by_entity.setdefault(entity, []).append(d)
            except Exception:
                if "Unknown" not in docs_by_entity:
                    doc_order.append("Unknown")
                docs_by_entity.setdefault("Unknown", []).append({"_raw_id": did})
        doc_rows = []
        span_rows = []
        for entity in doc_order:
            span_rows.append({"_before": len(doc_rows), "_text": f"[{entity}]"})
            for d in docs_by_entity[entity]:
                if "_raw_id" in d:
                    doc_rows.append({"Type": d["_raw_id"], "Format": "-", "Process": "-", "Memo": "-"})
                else:
                    process = d.get("document_process", "-") or "-"
                    if process == "N/A":
                        process = "-"
                    doc_rows.append({
                        "Type": d.get("document_type", "-"),
                        "Format": d.get("document_format", "-") or "-",
                        "Process": process,
                        "Memo": _format_value("memo-NEW2", d.get("memo-NEW2"), lang),
                    })
        _print_detail_table(doc_rows, ["Type", "Format", "Process", "Memo"], span_rows=span_rows)
        print()

    req_ids = s.get("data: requirements", [])
    if req_ids:
        print(f"\n{_dot(f'Requirements ({len(req_ids)})')}")
        req_rows = []
        for i, rid in enumerate(req_ids, 1):
            try:
                req = api_get(f"/api/1.1/obj/supply_requirement/{rid}")
                r = req.get("response", req)
                _last_requirements.append(r)
                req_stype = SERVICE_TYPE_TO_CODE.get(r.get("service_type", ""), r.get("service_type", "-") or "-")
                has_sol = "Yes" if r.get("has solution") else "No"
                incl = r.get("item_included", 0)
                sol_text = f"{has_sol} ({incl})" if incl else has_sol
                req_rows.append({
                    "#": str(i),
                    "Name": _format_value("requirement_name-NEW2", r.get("requirement_name-NEW2"), lang),
                    "Condition": _format_value("condition-NEW2", r.get("condition-NEW2"), lang),
                    "Type": req_stype,
                    "Solution": sol_text,
                })
            except Exception:
                req_rows.append({"#": str(i), "Name": rid, "Condition": "-", "Type": "-", "Solution": "-"})
        _print_detail_table(req_rows, ["#", "Name", "Condition", "Type", "Solution"])
        print()

    action_hints = []
    if req_ids:
        action_hints.append("Resolve requirement products: resolve <#>")
    if _as_list(s.get("qa-list")):
        action_hints.append("View product FAQs: faq")
    if action_hints:
        print()
        for hint in action_hints:
            print(f"  {DIM}{hint}{RESET}")


def fetch_product_requirements(product: dict) -> List[dict]:
    """Returns full supply_requirement records for the product's supply."""
    supply_id = product.get("supply_info")
    if not supply_id:
        return []
    try:
        supply = api_get(f"/api/1.1/obj/supply_all/{supply_id}")
    except Exception:
        return []
    s = supply.get("response", supply)
    req_ids = s.get("data: requirements", []) or []
    out = []
    for rid in req_ids:
        try:
            req = api_get(f"/api/1.1/obj/supply_requirement/{rid}")
            out.append(req.get("response", req))
        except Exception:
            out.append({"_id": rid, "_fetch_failed": True})
    return out


def scan_resolving_products(requirement: dict, jurisdiction_id: Optional[str]) -> List[dict]:
    """Return products that resolve a requirement, scoped to the given jurisdiction."""
    supply_ids = requirement.get("solution_specify_supply") or []
    if isinstance(supply_ids, str):
        supply_ids = [supply_ids]
    supplier_id = requirement.get("solution_specify_supplier")
    stype = requirement.get("service_type")

    if not supply_ids and supplier_id:
        sup_constraints = [
            {"key": "supplier_entity", "constraint_type": "equals", "value": supplier_id},
        ]
        if stype:
            sup_constraints.append({"key": "service_type", "constraint_type": "equals", "value": stype})
        if jurisdiction_id:
            sup_constraints.append({"key": "belonging_jurisdiction", "constraint_type": "equals", "value": jurisdiction_id})
        supplies = api_list("supply_all", sup_constraints)
        supply_ids = [s["_id"] for s in supplies]

    constraints = []
    if supply_ids:
        if len(supply_ids) == 1:
            constraints.append({"key": "supply_info", "constraint_type": "equals", "value": supply_ids[0]})
        else:
            constraints.append({"key": "supply_info", "constraint_type": "in", "value": supply_ids})
    if stype:
        constraints.append({"key": "service_type", "constraint_type": "equals", "value": stype})
    if jurisdiction_id:
        constraints.append({"key": "full-applicable-jurisdictions", "constraint_type": "contains", "value": jurisdiction_id})

    if not constraints:
        return []

    products = api_list("product:all", constraints)
    seen = set()
    unique = []
    for p in products:
        pid = p.get("_id")
        if pid not in seen:
            seen.add(pid)
            unique.append(p)
    return unique


def can_resolve_requirement(requirement: dict) -> bool:
    return bool(requirement.get("has solution"))


def requirement_resolution_scope(product: Optional[dict] = None) -> Optional[str]:
    if _last_search_country_id:
        return _last_search_country_id
    if not product:
        return None
    jurisdiction_id = product.get("belonging_jurisdiction")
    if jurisdiction_id:
        return jurisdiction_id
    applicable = product.get("full-applicable-jurisdictions") or []
    if isinstance(applicable, str):
        return applicable
    if isinstance(applicable, list) and applicable:
        return applicable[0]
    return None


def resolve_requirement_products(requirement: dict, jurisdiction_id: Optional[str]) -> List[dict]:
    """Resolve requirement products through the single shared CLI lookup path."""
    if not can_resolve_requirement(requirement):
        return []
    return scan_resolving_products(requirement, jurisdiction_id)


def cmd_resolve_requirement(args):
    global _last_requirements, _last_view_product, _last_lang
    if not _last_view_product or not _last_requirements:
        print("No product requirements in view. Run 'product <code>' then 'view <#>' first.", file=sys.stderr)
        return
    if not args:
        print(f"Usage: resolve <#>", file=sys.stderr)
        return

    try:
        idx = int(args[0])
    except ValueError:
        print(f"Invalid number: {args[0]}", file=sys.stderr)
        return

    if idx < 1 or idx > len(_last_requirements):
        print(f"Invalid index. Choose 1-{len(_last_requirements)}.", file=sys.stderr)
        return

    req = _last_requirements[idx - 1]
    lang = _last_lang
    name = _format_value("requirement_name-NEW2", req.get("requirement_name-NEW2"), lang)
    condition = _format_value("condition-NEW2", req.get("condition-NEW2"), lang)
    jurisdiction_id = requirement_resolution_scope(_last_view_product)
    jurisdiction = id_to_abbr(jurisdiction_id) if jurisdiction_id else "-"

    print(f"\n  {BOLD}Resolve requirement #{idx}:{RESET} {name}")
    if condition and condition != "-":
        print(f"  {DIM}Condition:{RESET} {condition}")
    print(f"  {DIM}Jurisdiction scope:{RESET} {jurisdiction}")

    if not can_resolve_requirement(req):
        print(f"\n  {DIM}This requirement has no TKEG solution. The client must handle it themselves.{RESET}")
        return

    print(f"\n  {DIM}Scanning resolving products...{RESET}")
    products = resolve_requirement_products(req, jurisdiction_id)
    _print_resolving_products(products, lang)


def cmd_faq(args):
    global _last_view_product, _last_lang
    if args:
        print("Usage: faq", file=sys.stderr)
        return
    if not _last_view_product:
        print("No product in view. Run 'product <code>' then 'view <#>' first.", file=sys.stderr)
        return

    supply_id = _last_view_product.get("supply_info")
    if not supply_id:
        print("Current product has no linked supply.", file=sys.stderr)
        return

    lang = _last_lang
    product_name = _product_label(_last_view_product, lang)
    _reset_dots()
    print(f"\n  {BOLD}Product FAQs:{RESET} {product_name}")
    print(f"  {DIM}Fetching FAQs...{RESET}")

    try:
        supply = api_get(f"/api/1.1/obj/supply_all/{supply_id}")
        s = supply.get("response", supply)
    except Exception as e:
        print(f"  Failed to fetch supply: {e}", file=sys.stderr)
        return

    faq_ids = _as_list(s.get("qa-list"))
    if not faq_ids:
        _print_faqs([])
        return

    faq_rows = []
    for i, fid in enumerate(faq_ids, 1):
        try:
            rec = api_get(f"/api/1.1/obj/frequent_questions/{fid}")
            faq = rec.get("response", rec)
            question = _format_value("question_new2", faq.get("question_new2"), lang)
            answer = _format_value("answer_new2", faq.get("answer_new2"), lang)
            faq_rows.append({
                "#": str(i),
                "Question": question,
                "Answer": answer,
            })
        except Exception:
            faq_rows.append({
                "#": str(i),
                "Question": fid,
                "Answer": "Failed to fetch FAQ.",
            })
    _print_faqs(faq_rows)


def cmd_product(args):
    global _last_products, _last_lang, _last_view_product
    global _last_search_country_id, _last_search_country_abbr
    _last_view_product = None
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
    _last_search_country_id = country["_id"]
    _last_search_country_abbr = country["abbr"]
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
