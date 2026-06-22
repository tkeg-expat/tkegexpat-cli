from __future__ import annotations

import re
import unicodedata
from typing import List, Optional

LOCALES = ("en_us", "zh_cn", "zh_tw", "es_es")

_MARKUP_RE = re.compile(
    r"\[/?"
    r"(?:ml|ol|ul|li|b|i|u|s|center|right|left|justify|font|color|size|link|img|br|hr|table|tr|td|th|thead|tbody)"
    r"(?:[=\s][^\]]*)?"
    r"\]"
)


def strip_markup(text: str) -> str:
    if not text or "[" not in text:
        return text or ""
    result = _MARKUP_RE.sub("", text)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def display_width(text: str) -> int:
    w = 0
    for ch in text:
        eaw = unicodedata.east_asian_width(ch)
        w += 2 if eaw in ("W", "F") else 1
    return w


def wrap_cjk(text: str, width: int) -> List[str]:
    if not text or text == "-":
        return [text or "-"]
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = []
        current_w = 0
        for word in words:
            ww = display_width(word)
            gap = 1 if current else 0
            if current_w + gap + ww > width and current:
                lines.append(" ".join(current))
                current = [word]
                current_w = ww
            else:
                current.append(word)
                current_w += gap + ww
        if current:
            lines.append(" ".join(current))
    return lines or ["-"]


def ljust_cjk(text: str, width: int) -> str:
    dw = display_width(text)
    return text + " " * max(0, width - dw)


def extract_lang(text: str, lang: Optional[str]) -> Optional[str]:
    # No language selected (e.g. logged out) → no extraction; callers fall back
    # to the raw field value.
    if not lang:
        return None
    pattern = r"\[" + re.escape(lang) + r"\](.*?)\[/" + re.escape(lang) + r"\]"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    if lang != "en_us":
        return extract_lang(text, "en_us")
    return None
