from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

needle = "crust"
for i, line in enumerate(lines):
    if needle in line.lower() and "b1" in "".join(lines[max(0,i-6):i+1]).lower():
        print(f"---match near line {i+1}---")
        for j in range(max(0,i-2), min(len(lines), i+3)):
            print(f"{j+1}: {lines[j]}")
        print()
