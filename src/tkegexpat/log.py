from __future__ import annotations

import sys

from .api import api_get, api_list
from .cit import _dot, _reset_dots, _print_detail_table

# Shared log viewer. The invoice / contract detail in view sets the context;
# `log` lists that record's entries.
#
#   invoice  -> invoice:log      linked by `invoice`   (max 4 per invoice)
#   contract -> contract:record  linked by `contract`  (max 4 per contract)
#
# Counts are tiny, so api_list (fetch-everything) is right here — no paging.
# The authoritative event date is `date-logged` / `record-date`: every row's
# `Created Date` is the 2026-04-24 portal migration stamp, and Bubble returns
# the rows unordered, so they are sorted client-side.

_SPEC = {
    "invoice": {
        "typename": "invoice:log",
        "link": "invoice",
        "date": "date-logged",
        "status": "invoice-status",
        "doc": "file-s3",
        "columns": ["#", "Date", "Status", "Doc", "By", "Text"],
        "title": "Invoice Log",
    },
    "contract": {
        "typename": "contract:record",
        "link": "contract",
        "date": "record-date",
        "status": "status",
        "doc": None,
        "columns": ["#", "Date", "Status", "By", "Text"],
        "title": "Contract Log",
    },
}

_ctx = {"kind": None, "id": None, "label": None}
_user_cache = {}


def set_context(kind, entity_id, label):
    """kind is 'invoice' or 'contract'. Called by the two detail renderers."""
    _ctx.update(kind=kind, id=entity_id, label=label)


def _author(uid):
    if not uid:
        return "-"
    if uid not in _user_cache:
        try:
            u = api_get(f"/api/1.1/obj/user/{uid}").get("response", {})
            _user_cache[uid] = u.get("user_name") or u.get("tkeg_user_id") or str(uid)
        except Exception:
            _user_cache[uid] = str(uid)
    return _user_cache[uid]


def _when(value):
    """'2025-06-19 09:32' — entries can land seconds apart, so keep the time.
    (A two-line date/time cell buys nothing: _print_detail_table measures the
    cell across the whole string, newline included, so the column is 16 either
    way.)"""
    if not value:
        return "-"
    s = str(value)
    if "T" not in s:
        return s
    day, rest = s.split("T", 1)
    return day + " " + rest[:5]


def _row(entry, i, spec):
    row = {
        "#": str(i),
        "Date": _when(entry.get(spec["date"])),
        "Status": entry.get(spec["status"]) or "-",
        "By": _author(entry.get("Created By")),
        "Text": (entry.get("text") or "").strip() or "-",
    }
    if spec["doc"]:
        row["Doc"] = "yes" if entry.get(spec["doc"]) else "-"
    return row


def cmd_log(args):
    spec = _SPEC.get(_ctx["kind"])
    if not spec or not _ctx["id"]:
        print("No invoice or contract in view. Open one first.", file=sys.stderr)
        return

    try:
        entries = api_list(spec["typename"], [
            {"key": spec["link"], "constraint_type": "equals", "value": _ctx["id"]},
        ])
    except Exception as e:
        print(f"  Failed to fetch log: {e}", file=sys.stderr)
        return

    entries.sort(key=lambda r: r.get(spec["date"]) or "")

    _reset_dots()
    label = f" {_ctx['label']}" if _ctx["label"] else ""
    print("\n" + _dot(f"{spec['title']}{label} ({len(entries)})"))
    if not entries:
        print("  No log entries.\n")
        return

    rows = [_row(e, i, spec) for i, e in enumerate(entries, 1)]
    _print_detail_table(rows, spec["columns"], char_wrap=["Text"])
    print()
