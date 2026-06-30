#!/usr/bin/env python3
"""Verify generated study pages.

Checks, over every *.html in the target dir (default: cwd):
  1. no residual vertical-form punctuation glyphs in the markup;
  2. every internal href resolves to an existing file;
  3. <ruby>/<rt> open and close tags are balanced.

Usage:  python3 check.py [dir]
Exit code 0 if all pass, 1 otherwise.
"""
import os
import re
import sys

VERTICAL = "︑︒﹁﹂﹃﹄︵︶"           # vertical-form glyphs that must be normalized away
HREF_RE = re.compile(r'href="([^"]+)"')


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    files = sorted(f for f in os.listdir(root) if f.endswith(".html"))
    if not files:
        print(f"no .html files in {root!r}")
        return 1

    problems = 0

    # 1) vertical glyphs
    print("=== 1) residual vertical-form glyphs (should be none) ===")
    for f in files:
        text = open(os.path.join(root, f), encoding="utf-8").read()
        hits = {g: text.count(g) for g in VERTICAL if g in text}
        if hits:
            problems += 1
            print(f"  ❌ {f}: {hits}")
    if not problems:
        print("  ✅ none")

    # 2) internal links
    print("\n=== 2) internal href targets resolve ===")
    link_problems = 0
    for f in files:
        text = open(os.path.join(root, f), encoding="utf-8").read()
        for tgt in HREF_RE.findall(text):
            if tgt.startswith(("http://", "https://", "#", "mailto:")):
                continue
            path = os.path.join(root, tgt.split("#", 1)[0])
            if not os.path.isfile(path):
                link_problems += 1
                print(f"  ❌ MISSING  {f} -> {tgt}")
    problems += link_problems
    if not link_problems:
        print("  ✅ all internal links resolve")

    # 3) ruby/rt balance
    print("\n=== 3) <ruby>/<rt> tag balance ===")
    bal_problems = 0
    for f in files:
        text = open(os.path.join(root, f), encoding="utf-8").read()
        ro, rc = text.count("<ruby>"), text.count("</ruby>")
        to, tc = text.count("<rt>"), text.count("</rt>")
        if ro != rc or to != tc:
            bal_problems += 1
            print(f"  ❌ {f}: <ruby>={ro}/{rc}  <rt>={to}/{tc}")
        elif ro:
            print(f"  ✅ {f}: <ruby>={ro}  <rt>={to}")
    problems += bal_problems

    print("\n" + ("✅ ALL CHECKS PASSED" if not problems else f"❌ {problems} problem(s) found"))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
