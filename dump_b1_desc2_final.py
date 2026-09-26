from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

print("===== bridgeData b1 desc2 full (lines 1281-1290) =====")
for i in range(1280, 1290):
    print(f"{i+1}: {lines[i]}")
