from pathlib import Path
import re

ROOT = Path(".").resolve()
p = ROOT / "index.html"
text = p.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()

targets = [
    "b1-body",
    "Giza",
    "Tiwanaku",
    "Gunung Padang",
    "Hal Saflieni",
    "pineal",
    "telepath",
    "OBE",
    "out-of-body",
    "empirical proof",
    "levitation achieved",
]

seen_lines = set()
for i, line in enumerate(lines):
    for t in targets:
        if t.lower() in line.lower():
            for j in range(max(0, i-1), min(len(lines), i+2)):
                seen_lines.add(j)

for j in sorted(seen_lines):
    print(f"{j+1}: {lines[j]}")
