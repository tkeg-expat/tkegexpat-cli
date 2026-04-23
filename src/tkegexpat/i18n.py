from __future__ import annotations

import re
from typing import Optional

LOCALES = ("en_us", "zh_cn", "zh_tw", "es_es")


def extract_lang(text: str, lang: str) -> Optional[str]:
    pattern = r"\[" + re.escape(lang) + r"\](.*?)\[/" + re.escape(lang) + r"\]"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    if lang != "en_us":
        return extract_lang(text, "en_us")
    return None
