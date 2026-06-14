from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Optional, Tuple

from . import product as product_mod
from .api import _request, api_list
from .auth import require_token, require_user_id
from .config import API_BASE
from .countries import id_to_abbr
from .i18n import display_width, extract_lang, ljust_cjk, strip_markup

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

IP_PROBE_URL = "https://cfmedia.tkegexpat.cn/web-version"
USER_AGENT_TAG = "TKEG CLI"

_session_cache: dict = {}
_last_view_cos: Optional[dict] = None


class _CosError(Exception):
    pass


def _err(msg: str):
    raise _CosError(msg)


def _resolve_product(arg: Optional[str]) -> dict:
    if arg is not None:
        try:
            idx = int(arg) - 1
        except ValueError:
            _err(f"invalid index: {arg!r}")
        plist = product_mod._last_products
        if not plist:
            _err("no product list loaded. Run `product <cc><svc>` first.")
        if idx < 0 or idx >= len(plist):
            _err(f"# out of range (1..{len(plist)})")
        return plist[idx]
    if not product_mod._last_view_product:
        _err("no product in view. Run `view <#>` on a product list first.")
    return product_mod._last_view_product


def _resolve_search_country() -> Tuple[str, str]:
    cc_id = product_mod._last_search_country_id
    cc_abbr = product_mod._last_search_country_abbr
    if not cc_id:
        _err("no search country in scope. Run `product <cc><svc>` first (e.g. `product usci`).")
    return cc_id, cc_abbr


def _probe_client_ip() -> Tuple[str, str]:
    if "ip" in _session_cache:
        return _session_cache["ip"], _session_cache["country"]

    req = urllib.request.Request(
        IP_PROBE_URL,
        headers={"User-Agent": "TKEG-CLI"},
        method="GET",
    )
    headers = None
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            headers = resp.headers
    except urllib.error.HTTPError as e:
        # The probe endpoint returns 400 by design; relevant data is in response headers.
        headers = e.headers
    except urllib.error.URLError as e:
        _err(f"could not reach IP probe ({IP_PROBE_URL}): {e}")

    ip = headers.get("true-client-ip-out") if headers else None
    cc = headers.get("true-client-country-code") if headers else None
    if not ip:
        _err("IP probe returned no `true-client-ip-out` header")
    if not cc:
        _err("IP probe returned no `true-client-country-code` header")
    _session_cache["ip"] = ip
    _session_cache["country"] = cc
    return ip, cc


def _get_user_record(user_id: str) -> dict:
    if "user" in _session_cache:
        return _session_cache["user"]
    token = require_token()
    data = _request(f"/api/1.1/obj/user/{user_id}", token)
    rec = data.get("response", data)
    if not rec or not rec.get("_id"):
        _err(f"could not fetch User record {user_id}")
    _session_cache["user"] = rec
    return rec


def _find_crm_entity_id() -> str:
    constraints = [{"key": "portal_user", "constraint_type": "is_not_empty"}]
    crms = api_list("entity_crm", constraints)
    if not crms:
        _err("no entity_crm record matched constraint portal_user is_not_empty")
    return crms[-1]["_id"]


def _build_payload(product: dict, search_country_id: str) -> dict:
    user_id = require_user_id()
    user = _get_user_record(user_id)

    lang = user.get("language") or _err("user.language is empty on User record")
    user_type = user.get("user_type") or _err("user.user_type is empty on User record")
    web_version = user.get("website-version") or _err("user.website-version is empty on User record")

    ip, ip_cc = _probe_client_ip()
    crm_id = _find_crm_entity_id()

    prod_id = product.get("_id") or _err("product missing _id")
    service_type = product.get("service_type") or _err("product missing service_type")
    currency = product.get("default_marking_currency") or _err("product missing default_marking_currency")
    price = product.get("corporate_price")
    if price is None:
        _err("product missing corporate_price")

    return {
        "user": user_id,
        "user_logged_in": True,
        "session_status": "OPEN",
        "session-language": lang,
        "main_product": prod_id,
        "service_type": service_type,
        "service_country/region": search_country_id,
        "marking_currency": currency,
        "session_total_value": price,
        "main_product_unit_price": price,
        "crm_entity": crm_id,
        "current_user_type": user_type,
        "ip_address": ip,
        "ip_jurisdiction": ip_cc,
        "user-agent": USER_AGENT_TAG,
        "website-version": web_version,
    }


def _render_payload(payload: dict, product: dict):
    lang = product_mod._last_lang or "en_us"
    raw_name = product.get("product-name-new2") or "-"
    name_disp = strip_markup(extract_lang(str(raw_name), lang) or str(raw_name))
    country_abbr = id_to_abbr(payload["service_country/region"])

    pairs = [
        ("user (3)", payload["user"]),
        ("user_logged_in (4)", "true"),
        ("session_status (5)", payload["session_status"]),
        ("session-language (6)", payload["session-language"]),
        ("main_product (8)", f"{payload['main_product']}  ({name_disp})"),
        ("service_type (10)", payload["service_type"]),
        ("service_country/region (11)", f"{payload['service_country/region']}  ({country_abbr})"),
        ("marking_currency (12)", payload["marking_currency"]),
        ("session_total_value (13)", str(payload["session_total_value"])),
        ("main_product_unit_price (14)", str(payload["main_product_unit_price"])),
        ("crm_entity (27)", payload["crm_entity"]),
        ("current_user_type (38)", payload["current_user_type"]),
        ("ip_address (39)", payload["ip_address"]),
        ("ip_jurisdiction (40)", payload["ip_jurisdiction"]),
        ("user-agent (41)", payload["user-agent"]),
        ("website-version (44)", payload["website-version"]),
    ]

    pad = "  "
    key_w = max(display_width(k) for k, _ in pairs)
    val_w = max(display_width(str(v)) for _, v in pairs)

    print(f"\n{pad}{BOLD}Check-out Session Draft{RESET}\n")
    print(f"{pad}{BOLD}{ljust_cjk('Field', key_w)} {DIM}│{RESET}{BOLD} {ljust_cjk('Value', val_w)}{RESET}")
    print(f"{pad}{DIM}{'─' * key_w}─┼─{'─' * val_w}{RESET}")
    for k, v in pairs:
        print(f"{pad}{ljust_cjk(k, key_w)} {DIM}│{RESET} {v}")


def _post_json(path: str, payload: dict) -> dict:
    token = require_token()
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_BASE + path, data=body, method="POST")
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("User-Agent", "tkegexpat-cli/0.7.0")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _extract_id(data: dict) -> Optional[str]:
    return data.get("id") or data.get("_id") or (data.get("response", {}) or {}).get("id")


def _post_check_out_session(payload: dict) -> Optional[str]:
    return _extract_id(_post_json("/api/1.1/obj/check_out_session", payload))


def _post_check_out_session_item(cos_id: str, product: dict) -> Optional[str]:
    price = product.get("corporate_price")
    payload = {
        "check_out_session": cos_id,
        "item": product["_id"],
        "item_quantity": 1,
        "item_unit_price": price,
        "sum": price,
    }
    return _extract_id(_post_json("/api/1.1/obj/check_out_session_item", payload))


def _req_name(req: dict, lang: str) -> str:
    raw = req.get("requirement_name-NEW2") or "-"
    return strip_markup(extract_lang(str(raw), lang) or str(raw))


def _req_condition(req: dict, lang: str) -> str:
    raw = req.get("condition-NEW2") or ""
    return strip_markup(extract_lang(str(raw), lang) or str(raw))


def _product_label(product: dict, lang: str) -> str:
    raw = product.get("product-name-new2") or "-"
    return strip_markup(extract_lang(str(raw), lang) or str(raw))


def _render_cos_summary(state: dict):
    cos_id = state["cos_id"]
    product = state["product"]
    payload = state["payload"]
    items = state["items"]
    lang = state.get("lang", "en_us")

    main_name = _product_label(product, lang)
    cur = payload["marking_currency"]
    price = payload["main_product_unit_price"]
    country_abbr = id_to_abbr(payload["service_country/region"])

    print(f"\n  {BOLD}Check-out Session{RESET} {DIM}{cos_id}{RESET}")
    print(f"  {DIM}Country:{RESET} {country_abbr}    "
          f"{DIM}Status:{RESET} {payload['session_status']}    "
          f"{DIM}Currency:{RESET} {cur}")
    print(f"  {DIM}Main product:{RESET} {main_name}  {DIM}({cur} {price}){RESET}")

    if items:
        total = (price or 0)
        print(f"\n  {BOLD}Attached items ({len(items)}){RESET}")
        for i, it in enumerate(items, 1):
            p = it["product"]
            iname = _product_label(p, lang)
            ic = p.get("default_marking_currency", "")
            ip_ = p.get("corporate_price", "-")
            try:
                total += float(ip_)
            except (TypeError, ValueError):
                pass
            print(f"    {i}. {iname}  {DIM}({ic} {ip_}){RESET}")
        print(f"\n  {BOLD}Total:{RESET} {cur} {total}")
    else:
        print(f"\n  {DIM}No additional items attached.{RESET}")


def _pick_resolving_product(products: list, lang: str) -> Optional[dict]:
    if not products:
        print(f"    {DIM}No TKEG product found. Skipping.{RESET}")
        return None

    if len(products) == 1:
        p = products[0]
        name = _product_label(p, lang)
        cur = p.get("default_marking_currency", "")
        price = p.get("corporate_price", "-")
        print(f"    Found 1: {name}  {DIM}({cur} {price}){RESET}")
        try:
            ans = input(f"    Add this? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        return p if ans == "y" else None

    print(f"    Found {len(products)}:")
    for i, p in enumerate(products, 1):
        name = _product_label(p, lang)
        cur = p.get("default_marking_currency", "")
        price = p.get("corporate_price", "-")
        print(f"      {i}. {name}  {DIM}({cur} {price}){RESET}")
    try:
        ans = input(f"    Pick [1-{len(products)} / s=skip]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if ans in ("s", "skip", ""):
        return None
    try:
        idx = int(ans) - 1
    except ValueError:
        print(f"    {DIM}Invalid choice — skipping.{RESET}")
        return None
    if idx < 0 or idx >= len(products):
        print(f"    {DIM}Out of range — skipping.{RESET}")
        return None
    return products[idx]


def _walk_requirements(state: dict):
    cos_id = state["cos_id"]
    product = state["product"]
    payload = state["payload"]
    lang = state.get("lang", "en_us")

    print(f"\n  {DIM}Fetching product requirements...{RESET}")
    reqs = product_mod.fetch_product_requirements(product)

    no_sol = [r for r in reqs if not product_mod.can_resolve_requirement(r)]
    solvable = [r for r in reqs if product_mod.can_resolve_requirement(r)]

    if no_sol:
        print(f"\n  {BOLD}Client must handle these themselves{RESET} {DIM}(no TKEG solution){RESET}")
        for r in no_sol:
            print(f"    • {_req_name(r, lang)}")

    if not solvable:
        print(f"\n  {DIM}No resolvable requirements.{RESET}")
        return

    print(f"\n  {BOLD}{len(solvable)} resolvable requirement(s){RESET}")
    jurisdiction_id = payload["service_country/region"]

    for i, req in enumerate(solvable, 1):
        name = _req_name(req, lang)
        cond = _req_condition(req, lang)

        print(f"\n  [{i}/{len(solvable)}] {BOLD}{name}{RESET}")
        if cond and cond != "-":
            print(f"      {DIM}Condition: {cond}{RESET}")

        try:
            ans = input(f"    Can the client provide this themselves? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Walkthrough interrupted.")
            return

        if ans == "y":
            continue

        print(f"    {DIM}Scanning resolving products...{RESET}")
        candidates = product_mod.resolve_requirement_products(req, jurisdiction_id)
        chosen = _pick_resolving_product(candidates, lang)
        if chosen is None:
            continue

        try:
            new_id = _post_check_out_session_item(cos_id, chosen)
            state["items"].append({"id": new_id, "product": chosen})
            print(f"    {BOLD}✓{RESET} Created cos_item: {DIM}{new_id}{RESET}  ({_product_label(chosen, lang)})")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"    {BOLD}✗{RESET} cos_item POST failed: HTTP {e.code}\n      {body}", file=sys.stderr)
        except Exception as e:
            print(f"    {BOLD}✗{RESET} cos_item POST failed: {e}", file=sys.stderr)


def cmd_view_cos(args):
    if not _last_view_cos:
        print("  No check-out session in scope. Run `cos create` first.", file=sys.stderr)
        return
    _render_cos_summary(_last_view_cos)


def cmd_cos(args):
    global _last_view_cos
    if not args:
        print("Usage: cos create [#]", file=sys.stderr)
        return None
    sub = args[0]
    if sub != "create":
        print(f"Unknown cos subcommand: {sub}", file=sys.stderr)
        print("Usage: cos create [#]", file=sys.stderr)
        return None

    try:
        product = _resolve_product(args[1] if len(args) > 1 else None)
        search_country_id, search_country_abbr = _resolve_search_country()
        print(f"  Building check-out session draft for {search_country_abbr.upper()}...")
        payload = _build_payload(product, search_country_id)
    except _CosError as e:
        print(f"  Error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return None

    _render_payload(payload, product)

    try:
        confirm = input(f"\n  {BOLD}Create check-out session?{RESET} [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return None
    if confirm != "y":
        print("  Cancelled.")
        return None

    print("  Creating...")
    try:
        new_id = _post_check_out_session(payload)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  POST failed: HTTP {e.code}\n  {body}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  POST failed: {e}", file=sys.stderr)
        return None

    print(f"\n  {BOLD}✓{RESET} Created check_out_session: {BOLD}{new_id}{RESET}")

    state = {
        "cos_id": new_id,
        "product": product,
        "payload": payload,
        "items": [],
        "lang": product_mod._last_lang or "en_us",
    }
    _last_view_cos = state

    _render_cos_summary(state)
    _walk_requirements(state)
    _render_cos_summary(state)

    return True
