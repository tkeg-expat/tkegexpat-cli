# TKEG Expat CLI — UI Design Rules

## Core principles

1. **Structured data must be in tables.** Key-value pairs, lists of records, memos — all use table layout. No free-form indented text blocks.
2. **Always wrap text in tables.** Columns have a max width; long content wraps to multiple lines within the cell. Tables never overflow the terminal.

## Visual style

Inspired by Claude Code's terminal aesthetic:

- **Box-drawing borders** — use `─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼` instead of `-`, `|`, `+`.
- **Bold headers** — ANSI bold (`\033[1m`) for table headers and section titles.
- **Dim separators** — ANSI dim (`\033[2m`) for table borders so data stands out.
- **Section titles** — bold text, no box, preceded by a blank line.
- **Consistent indent** — 2-space base indent for all output.
- **Max column width** — 40 characters default; text wraps within cells.
- **No trailing decorations** — no `===` or `***` borders around sections.

## Color usage

| Element | ANSI code | Purpose |
|---|---|---|
| Section title | `\033[1m` (bold) | Draw eye to structure |
| Table header row | `\033[1m` (bold) | Distinguish headers from data |
| Table borders | `\033[2m` (dim) | Recede visually behind data |
| Hint / prompt text | `\033[2m` (dim) | De-emphasize helper text |
| Error text | `\033[31m` (red) | Errors to stderr |
| Data cells | plain | Maximum readability |

Always reset with `\033[0m` after styled output.

## Table anatomy

```
  Header1 │ Header2 │ Header3      ← bold
  ────────┼─────────┼──────────    ← dim
  value   │ value   │ long value   ← plain
          │         │ wraps here
  value   │ value   │ value
```

- Column separator: ` │ ` (space, box-draw vertical, space)
- Row separator: `─` repeated per column width, joined by `┼`
- No outer border (top/bottom/left/right)
- Spanning rows (e.g. entity group headers in documents) use full-width text on their own line, followed by the separator line

## Key-value tables

For product/supply detail views:

```
  Field              │ Value
  ───────────────────┼──────────────
  Product ID         │ 1111111567
  Service Type       │ CI
```

Same box-drawing style, two columns, field names left-aligned.
