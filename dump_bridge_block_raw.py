from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

start, end = 1255, 1305
for i in range(start, min(end, len(lines))):
    print(f"{i+1}: {lines[i]}")
