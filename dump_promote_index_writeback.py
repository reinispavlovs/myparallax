import re
from pathlib import Path

p = Path("scripts/promote_drafts.py")
text = p.read_text(encoding="utf-8")
lines = text.splitlines()

# Find the index.json write block: look for "index_data" or "topics[" assignments
hits = []
for i, line in enumerate(lines, start=1):
    if any(kw in line for kw in ["index_data", "topics[", "credibility_score", "risk_level", "bump_weight", "def promote_one", "index.json"]):
        hits.append(i)

# Print contiguous context around the densest cluster (likely the index update block)
print("=== Hit line numbers ===")
print(hits)

print()
print("=== Full context: 15 lines before/after each hit cluster ===")
seen = set()
for h in hits:
    lo, hi = max(1, h-10), min(len(lines), h+10)
    key = (lo, hi)
    if key in seen:
        continue
    seen.add(key)
    print(f"--- lines {lo}-{hi} ---")
    for n in range(lo, hi+1):
        print(f"{n:4d}: {lines[n-1]}")
    print()
