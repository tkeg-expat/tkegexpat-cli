from __future__ import annotations

import re
import sys

from .api import api_list

# Shared `--crm <_id>` / `--client <_id | tkeg-id>` constraint flags for the
# commands whose records carry crm / client references (project, project-item,
# company, cos). Bubble constraints only accept _id, so a client tkeg id is
# resolved to its entity_client _id first (entity_client.Slug == the tkeg id).


def _resolve_client_id(value):
    """entity_client _id -> itself; numeric tkeg id -> entity_client _id via Slug."""
    value = value.strip()
    if re.fullmatch(r"\d+x\d+", value):
        return value
    try:
        rows = api_list("entity_client", [
            {"key": "Slug", "constraint_type": "equals", "value": value},
        ])
    except Exception:
        rows = []
    return rows[0]["_id"] if rows else None


def parse_filters(args, crm_field=None, client_field=None):
    """Pull --crm / --client out of args.

    Returns (positional_args, extra_constraints, ok). ok=False means an error was
    already printed and the caller should abort.
    """
    positional, constraints = [], []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--crm", "--client"):
            val = args[i + 1] if i + 1 < len(args) else None
            if not val:
                print(f"{a} needs a value.", file=sys.stderr)
                return positional, constraints, False
            field = crm_field if a == "--crm" else client_field
            if not field:
                print(f"{a} is not supported for this command.", file=sys.stderr)
                return positional, constraints, False
            if a == "--client":
                cid = _resolve_client_id(val)
                if not cid:
                    print(f"No client found for '{val}'.", file=sys.stderr)
                    return positional, constraints, False
                if cid != val:
                    print(f"  (client tkeg id {val} → {cid})")
                val = cid
            constraints.append({"key": field, "constraint_type": "equals", "value": val})
            i += 2
        else:
            positional.append(a)
            i += 1
    return positional, constraints, True
