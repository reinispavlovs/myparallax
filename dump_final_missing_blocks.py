from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

# Exact key-based context capture: print 6 lines before/after each match
targets = [
    "m.known", "flatline", "m1-body", "m2-body", "m3-body",
]

# metaphysicsData block markers - find by index comments/ids
meta_markers = ["metaphysics", "Giza", "Barabar", "Tiwanaku"]

def dump_hits(keys, label):
    print("="*70)
    print(label)
    print("="*70)
    for i, line in enumerate(lines, start=1):
        for k in keys:
            if k in line:
                start = max(0, i-2)
                end = min(len(lines), i+3)
                for j in range(start, end):
                    print(f"{j+1}: {lines[j]}")
                print("---")
                break

dump_hits(targets, "m-body / m.known / flatline hits")
dump_hits(meta_markers, "metaphysics block markers")
