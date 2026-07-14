from __future__ import annotations

import sys

from .api import api_get, api_page
from .cit import _dot, _reset_dots, _print_detail_table, DIM, RESET
from .i18n import strip_markup

# Shared message viewer. The current detail page (project / project-item /
# company) sets the context; `message` pages through that entity's messages.
#
# Messages are `message:project+company+todo` with TWO link fields:
#   entity: project   (~11k msgs)   entity: company  (~1k msgs)
# There is no project-item link, so a project-item shows its belonging
# project's messages (kind "project", id = belonging project).

PAGE_SIZE = 20
MSG_COLUMNS = ["#", "Date", "From", "Message"]

_ctx = {"kind": None, "id": None, "label": None, "cursor": 0}
_user_cache = {}


def set_context(kind, entity_id, label):
    """kind is 'project' or 'company'. Resets paging to the first page."""
    _ctx.update(kind=kind, id=entity_id, label=label, cursor=0)


def _constraint():
    key = "entity: company" if _ctx["kind"] == "company" else "entity: project"
    return [{"key": key, "constraint_type": "equals", "value": _ctx["id"]}]


def _sender(uid):
    if not uid:
        return "-"
    if uid not in _user_cache:
        try:
            u = api_get(f"/api/1.1/obj/user/{uid}").get("response", {})
            _user_cache[uid] = u.get("user_name") or u.get("tkeg_user_id") or str(uid)[:10]
        except Exception:
            _user_cache[uid] = str(uid)[:10]
    return _user_cache[uid]


def _date(value):
    if not value:
        return "-"
    s = str(value)
    return s.split("T")[0] if "T" in s else s


def cmd_message(args):
    if not _ctx["id"]:
        print("No project or company in view. Open a project / project-item / company detail first.", file=sys.stderr)
        return

    advance = bool(args) and args[0].lower() == "next"
    if not advance:
        _ctx["cursor"] = 0
    start = _ctx["cursor"]

    try:
        page = api_page(
            "message:project+company+todo", _constraint(),
            cursor=start, limit=PAGE_SIZE,
            sort_field="NEW_date_created", descending=True,
        )
    except Exception as e:
        print(f"  Failed to fetch messages: {e}", file=sys.stderr)
        return

    results = page["results"]
    _reset_dots()
    if not results:
        if advance:
            print("  No more messages.")
        else:
            print(f"\n{_dot('Messages — ' + (_ctx['label'] or ''))}")
            print("  No messages.\n")
        return

    total = start + page["count"] + page["remaining"]
    header = f"Messages — {_ctx['label']}  (newest first, {start + 1}–{start + page['count']} of {total})"
    print(f"\n{_dot(header)}")

    rows = []
    for i, m in enumerate(results, 1):
        text = strip_markup(m.get("message") or "").strip() or "-"
        rows.append({
            "#": str(start + i),
            "Date": _date(m.get("NEW_date_created") or m.get("Created Date")),
            "From": _sender(m.get("Created By")),
            "Message": text,
        })
    _print_detail_table(rows, MSG_COLUMNS)

    _ctx["cursor"] = start + page["count"]
    if page["remaining"] > 0:
        print(f"\n  {DIM}Next page: message next  ({page['remaining']} more){RESET}")
    print()
