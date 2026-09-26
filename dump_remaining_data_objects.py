from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
text = p.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()

keywords = ["metaphysicsData", "gapDetailsData", "consciousnessData"]

for kw in keywords:
    print(f"\n\n========== BLOCK: {kw} ==========")
    idx = None
    for i, line in enumerate(lines):
        if kw in line and ("=" in line or "const" in line):
            idx = i
            break
    if idx is None:
        print(f"[NOT FOUND] {kw}")
        continue
    depth = 0
    started = False
    end = idx
    for j in range(idx, min(idx + 400, len(lines))):
        depth += lines[j].count("{") - lines[j].count("}")
        if "{" in lines[j]:
            started = True
        end = j
        if started and depth <= 0:
            break
    for j in range(idx, end + 1):
        print(f"{j+1}: {lines[j]}")
