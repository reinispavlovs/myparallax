from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

targets = ["Sheldrake", "levitation", "levitat", "cat-phys-body",
           "cat-phys-desc", "dampens", "activate", "stimulat"]

seen = set()
for i, line in enumerate(lines, start=1):
    for k in targets:
        if k.lower() in line.lower() and i not in seen:
            start = max(0, i-1)
            end = min(len(lines), i+2)
            for j in range(start, end):
                print(f"{j+1}: {lines[j]}")
                seen.add(j+1)
            print("---")
            break
