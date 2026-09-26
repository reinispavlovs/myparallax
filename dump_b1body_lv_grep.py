from pathlib import Path
import re

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

targets = ["b1-body", "b1-head", "b1-sub", "bridge-desc", "bridge-title"]

for i, line in enumerate(lines, start=1):
    for t in targets:
        if f"'{t}'" in line:
            print(f"{i}: {line}")
