from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

targets = ["b2-sub", "b2-body", "b3-head", "b3-sub", "b3-body",
           "c2-list-item", "c2-head", "c2-body", "cons-sec"]

for i, line in enumerate(lines, start=1):
    for k in targets:
        if k in line:
            start = max(0, i-1)
            end = min(len(lines), i+2)
            for j in range(start, end):
                print(f"{j+1}: {lines[j]}")
            print("---")
            break
