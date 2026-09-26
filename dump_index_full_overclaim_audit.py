import re
from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"

RISK_PATTERN = re.compile(
    r"(proven|proves|confirmed|confirms|demonstrate[s]?\b|identical\b|proving|established fact|inducing\b)",
    re.IGNORECASE
)

if not p.exists():
    print("[FILE NOT FOUND]")
else:
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    print("=" * 70)
    print(f"Total lines in index.html: {len(lines)}")
    print("=" * 70)

    site_name_matches = list(re.finditer(r'name:\s*\{\s*LV:\s*"([^"]*)",\s*EN:\s*"([^"]*)"', text))
    print(f"\nTotal megalith site entries found: {len(site_name_matches)}\n")

    meta_matches = list(re.finditer(r'metaphysics:\s*\{\s*LV:\s*"([^"]*)",\s*EN:\s*"([^"]*)"\s*\}', text, re.DOTALL))
    print(f"Total 'metaphysics' blocks found: {len(meta_matches)}\n")

    print("-" * 70)
    print("METAPHYSICS BLOCK AUDIT (EN text only)")
    print("-" * 70)
    for i, m in enumerate(meta_matches, 1):
        en_text = m.group(2)
        flagged = bool(RISK_PATTERN.search(en_text))
        marker = "[FLAG]" if flagged else "[ok]  "
        line_no = text[:m.start()].count("\n") + 1
        print(f"{marker} Block {i} (line ~{line_no}): {en_text[:140]}")

    print()
    print("-" * 70)
    print("ENGINEERING BLOCK AUDIT (EN text only) - secondary check")
    print("-" * 70)
    eng_matches = list(re.finditer(r'engineering:\s*\{\s*LV:\s*"([^"]*)",\s*EN:\s*"([^"]*)"\s*\}', text, re.DOTALL))
    for i, m in enumerate(eng_matches, 1):
        en_text = m.group(2)
        flagged = bool(RISK_PATTERN.search(en_text))
        marker = "[FLAG]" if flagged else "[ok]  "
        line_no = text[:m.start()].count("\n") + 1
        print(f"{marker} Block {i} (line ~{line_no}): {en_text[:140]}")

    print()
    print("-" * 70)
    print("MODAL TEXT BLOCKS (m1-body, m2-body, m3-body, c1-list, c2-list-*)")
    print("-" * 70)
    for key in ["m1-body", "m2-body", "m3-body", "c1-list", "c2-list-item1", "c2-list-item2", "c2-list-item3"]:
        pat = re.compile(rf"'{re.escape(key)}':\s*[\"'](.+?)[\"'],?\s*\n", re.DOTALL)
        m = pat.search(text)
        if m:
            snippet = m.group(1)[:200]
            flagged = bool(RISK_PATTERN.search(snippet))
            marker = "[FLAG]" if flagged else "[ok]  "
            print(f"{marker} {key}: {snippet}")
        else:
            print(f"[??]   {key}: NOT FOUND")

    print()
    print("=" * 70)
    print("DONE - review [FLAG] entries above for hedging patch scope")
    print("=" * 70)
