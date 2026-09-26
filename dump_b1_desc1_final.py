from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

print("===== bridgeData b1 tag/title/desc1 (lines 1260-1282) =====")
for i in range(1259, 1282):
    print(f"{i+1}: {lines[i]}")
