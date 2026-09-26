"""
dump_index_modal_and_cataclysm_check.py
1. Dumps the full modal content block in index.html around lines 960-1010
   to see all m1-m4 body entries (context for isomorphism/NDE overclaim discovery).
2. Scans content/articles/cyclical_cataclysms_precession.html directly for
   unhedged causal claims (proven/proves/confirms) near platinum/precession terms.
3. Scans tribunal.html for the same modal pattern to check if it duplicates
   the index.html overclaim text.
"""
import re
from pathlib import Path

ROOT = Path(".").resolve()
risk_patterns = re.compile(
    r"(proven|proves|confirms|confirmed|demonstrates conclusively|established fact)",
    re.IGNORECASE
)

def dump_lines(path, start, end, label):
    print("=" * 70)
    print(f"{label}: {path.name} lines {start}-{end}")
    print("=" * 70)
    if not path.exists():
        print("  [FILE NOT FOUND]")
        return
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i in range(max(0, start - 1), min(len(lines), end)):
        print(f"{i+1:5d}: {lines[i]}")
    print()

# 1. index.html modal context
dump_lines(ROOT / "index.html", 955, 1015, "STEP 1")

# 2. Direct scan of promoted cataclysm article
print("=" * 70)
print("STEP 2: content/articles/cyclical_cataclysms_precession.html scan")
print("=" * 70)
p = ROOT / "content" / "articles" / "cyclical_cataclysms_precession.html"
if p.exists():
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    keyword_hits = [i for i, l in enumerate(lines, 1)
                    if any(k in l.lower() for k in ["platinum", "precession", "orbital", "12,800", "12800"])]
    print(f"  Total lines: {len(lines)}, keyword-hit lines: {len(keyword_hits)}")
    any_risk = False
    for i, line in enumerate(lines, 1):
        if risk_patterns.search(line):
            any_risk = True
            print(f"  [RISK] Line {i}: {line.strip()[:160]}")
    if not any_risk:
        print("  [CLEAN] No 'proven/proves/confirms' language found in promoted article.")
else:
    print("  [FILE NOT FOUND]")
print()

# 3. tribunal.html modal scan - find m1-m4 body pattern context
print("=" * 70)
print("STEP 3: tribunal.html modal body scan")
print("=" * 70)
t = ROOT / "tribunal.html"
if t.exists():
    ttext = t.read_text(encoding="utf-8", errors="replace")
    tlines = ttext.splitlines()
    for i, line in enumerate(tlines, 1):
        if re.search(r"m\d-body", line, re.IGNORECASE) or risk_patterns.search(line):
            print(f"  Line {i}: {line.strip()[:160]}")
else:
    print("  [FILE NOT FOUND]")
