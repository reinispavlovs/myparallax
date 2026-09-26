from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

targets = [630, 650, 793, 805, 915, 925, 968, 980]
seen = set()
for a in range(0, len(targets), 2):
    start, end = targets[a], targets[a+1]
    for i in range(start, min(end, len(lines))):
        if i in seen:
            continue
        seen.add(i)
        print(f"{i+1}: {lines[i]}")
    print("----")
