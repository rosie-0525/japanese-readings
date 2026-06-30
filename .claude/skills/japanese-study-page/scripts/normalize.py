#!/usr/bin/env python3
"""Normalize source OCR text for use in a study page.

Converts vertical-form punctuation to horizontal forms and drops 〔PDF p.N〕 markers.
Furigana and 白文 OCR correction are NOT done here — that needs human/model judgment.

Usage:
    python3 normalize.py < snippet.txt
    sed -n '17,21p' extracted/01_公案小説.txt | python3 normalize.py
"""
import re
import sys

MAP = {
    "︑": "、", "︒": "。",
    "﹁": "「", "﹂": "」",
    "﹃": "『", "﹄": "』",
    "︵": "（", "︶": "）",
}
PAGE_MARKER = re.compile(r"〔PDF\s*p\.?\s*\d+〕")


def normalize(text: str) -> str:
    for a, b in MAP.items():
        text = text.replace(a, b)
    text = PAGE_MARKER.sub("", text)
    # collapse blank lines created by removed markers
    lines = [ln.rstrip() for ln in text.splitlines()]
    out, prev_blank = [], False
    for ln in lines:
        blank = (ln.strip() == "")
        if blank and prev_blank:
            continue
        out.append(ln)
        prev_blank = blank
    return "\n".join(out).strip() + "\n"


if __name__ == "__main__":
    sys.stdout.write(normalize(sys.stdin.read()))
