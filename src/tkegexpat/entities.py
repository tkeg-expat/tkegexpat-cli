from __future__ import annotations

from .api import api_get

# Every non-prime entity type links back to entity:prime (which holds
# `entity_name`), but the link field name differs per type:
#   entity_client / entity_crm      -> "prime_entity"
#   entity:company:all              -> "prime entity"  (space)
#   entity:tkegexpat                -> "element: prime entity"
_PRIME_LINK_FIELDS = ("prime_entity", "prime entity", "element: prime entity")


def _get(path):
    try:
        return api_get(path).get("response", {}) or {}
    except Exception:
        return {}


def resolve_prime_name(ref_id, typename):
    """Fetch an entity ref -> its prime entity -> `entity_name`, or None."""
    if not ref_id:
        return None
    rec = _get(f"/api/1.1/obj/{typename}/{ref_id}")
    prime_id = None
    for field in _PRIME_LINK_FIELDS:
        if rec.get(field):
            prime_id = rec[field]
            break
    if not prime_id:
        return None
    return _get(f"/api/1.1/obj/entity:prime/{prime_id}").get("entity_name")


def entity_cell(ref_id, typename):
    """Value for a KV cell: resolved entity name over its UID, or '-' if empty."""
    if not ref_id:
        return "-"
    name = resolve_prime_name(ref_id, typename)
    return f"{name}\n{ref_id}" if name else str(ref_id)


def prime_name(prime_id):
    """entity:prime -> entity_name (for refs that already point at a prime)."""
    if not prime_id:
        return None
    return _get(f"/api/1.1/obj/entity:prime/{prime_id}").get("entity_name")


def project_label(project_id):
    """'project_name (TKEG <id>)' over the project UID, or '-' if empty."""
    if not project_id:
        return "-"
    pr = _get(f"/api/1.1/obj/projects:all/{project_id}")
    if not pr:
        return str(project_id)
    name = pr.get("project_name") or "-"
    tid = pr.get("tkeg_project_id")
    tail = f"  (TKEG {tid})" if tid else ""
    return f"{name}{tail}\n{project_id}"


def product_name(product_id):
    """product:all -> localized `product-name-new2`, or '-' if empty."""
    if not product_id:
        return "-"
    from .config import effective_language
    from .i18n import extract_lang, strip_markup
    raw = _get(f"/api/1.1/obj/product:all/{product_id}").get("product-name-new2") or ""
    if not raw:
        return str(product_id)
    lang = effective_language()
    ext = extract_lang(raw, lang) if lang else None
    return strip_markup(ext) if ext else strip_markup(raw)
