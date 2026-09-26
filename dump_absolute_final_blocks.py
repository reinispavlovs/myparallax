from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

ranges = [
    (220, 260, "3-Pillars b1/b2/b3 body block (LV, HTML)"),
    (860, 900, "3-Pillars b1/b2/b3 body block (EN, i18n)"),
    (795, 802, "m-body LV (context)"),
    (970, 980, "m-body EN (context)"),
    (910, 925, "c2-body / c-desc context"),
]

for start, end, label in ranges:
    print(f"\n===== {label} (lines {start}-{end}) =====")
    for i in range(start-1, min(end, len(lines))):
        print(f"{i+1}: {lines[i]}")
