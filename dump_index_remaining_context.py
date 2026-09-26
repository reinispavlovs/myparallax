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

dump_range("c2-list full block", 1330, 1360)
dump_range("consciousnessData.isomorphism full", 1328, 1345)
dump_range("bridgeData b2 full (desc2)", 1287, 1300)
dump_range("bridgeData b3 full", 1300, 1313)
