from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

# Precise line-range dumps for the 4 remaining raw blocks
ranges = [
    (1280, 1315, "bridgeData b1/b2 desc1/desc2"),
    (1149, 1200, "gapDetailsData (all topics, known+missing)"),
    (1316, 1345, "consciousnessData"),
]

for start, end, label in ranges:
    print(f"\n===== {label} (lines {start}-{end}) =====")
    for i in range(start-1, min(end, len(lines))):
        print(f"{i+1}: {lines[i]}")

# Separately grep for c2-list explicitly (key may be elsewhere)
print("\n===== c2-list occurrences =====")
for i, line in enumerate(lines):
    if "c2-list" in line:
        for j in range(max(0,i-1), min(len(lines), i+2)):
            print(f"{j+1}: {lines[j]}")
