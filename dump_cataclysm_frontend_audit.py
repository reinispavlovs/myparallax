"""
dump_cataclysm_frontend_audit.py
Locates cataclysm/precession-related frontend HTML files and scans them
for unhedged causal claims linking the platinum anomaly to orbital cycles.
"""
import re
from pathlib import Path

ROOT = Path(".").resolve()

# Step 1: find candidate HTML files by name
name_keywords = ["cataclysm", "precession", "younger-dryas", "younger_dryas", "impact"]
candidates = []
for p in ROOT.rglob("*.html"):
    if "_archive" in p.parts or "_history" in p.parts:
        continue
    lname = p.name.lower()
    if any(k in lname for k in name_keywords):
        candidates.append(p)

print("=" * 70)
print("STEP 1: Filename-based candidates")
print("=" * 70)
if candidates:
    for c in candidates:
        print(f"  {c.relative_to(ROOT)}")
else:
    print("  None found by filename.")

# Step 2: scan ALL top-level html files for cataclysm-related content
# (in case the topic lives inside tribunal.html / index.html / a shared page)
print()
print("=" * 70)
print("STEP 2: Content-based scan (all root-level .html, non-archive)")
print("=" * 70)

content_keywords = ["platinum", "precession", "younger dryas", "12,800", "12800", "cataclysm"]
risk_patterns = re.compile(
    r"(proven|proves|confirms|confirmed|demonstrates conclusively|established fact)",
    re.IGNORECASE
)

all_html = [p for p in ROOT.glob("*.html")]
for p in all_html:
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  [ERROR reading {p.name}]: {e}")
        continue

    lower = text.lower()
    hits = [k for k in content_keywords if k in lower]
    if not hits:
        continue

    print(f"\n--- {p.name} ---")
    print(f"  Contains keywords: {hits}")

    # find risky phrasing near cataclysm-related content
    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        ll = line.lower()
        if any(k in ll for k in content_keywords) and risk_patterns.search(line):
            snippet = line.strip()[:160]
            print(f"  [RISK] Line {i}: {snippet}")

    # also flag lines with risk words even without keyword overlap on same line,
    # if within +/- 3 lines of a keyword hit (context proximity)
    keyword_line_nums = [i for i, l in enumerate(lines, start=1) if any(k in l.lower() for k in content_keywords)]
    for i, line in enumerate(lines, start=1):
        if risk_patterns.search(line):
            near = any(abs(i - kl) <= 3 for kl in keyword_line_nums)
            if near and not any(k in line.lower() for k in content_keywords):
                snippet = line.strip()[:160]
                print(f"  [RISK-PROXIMITY] Line {i}: {snippet}")

print()
print("=" * 70)
print("DONE")
print("=" * 70)
