from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

def dump_range(label, start, end):
    print("=" * 70)
    print(f"{label}  (lines {start}-{end})")
    print("=" * 70)
    for i in range(start, end + 1):
        if 0 <= i - 1 < len(lines):
            print(f"{i}: {lines[i-1]}")
    print()

dump_range("CONTEXT: b1-body area", 858, 872)
dump_range("CONTEXT: metaphysics Block 1 (Giza)", 995, 1006)
dump_range("CONTEXT: metaphysics Block 4", 1038, 1050)
dump_range("CONTEXT: metaphysics Block 5 (Tiwanaku)", 1052, 1064)
dump_range("CONTEXT: metaphysics Block 11", 1138, 1148)
dump_range("CONTEXT: 'Verified/mapped' block", 1148, 1168)
dump_range("CONTEXT: 'Acoustic levitation achieved' block", 1270, 1292)
dump_range("CONTEXT: m1/m2/m3-body LV", 793, 802)
dump_range("CONTEXT: m1/m2/m3-body EN", 968, 977)
dump_range("CONTEXT: c2-list items", 1300, 1330)
