from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
text = p.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()

out = []

def dump_range(label, start, end):
    out.append(f"\n===== {label} (lines {start}-{end}) =====")
    for i in range(start-1, min(end, len(lines))):
        out.append(f"{i+1}: {lines[i]}")

dump_range("bridgeData b2 desc1/desc2 + b3 full", 1290, 1345)

idx = text.find("const gapDetailsData")
if idx != -1:
    start_line = text[:idx].count("\n") + 1
    dump_range("gapDetailsData FULL", start_line, start_line + 90)

idx2 = text.find("const consciousnessData")
if idx2 != -1:
    start_line2 = text[:idx2].count("\n") + 1
    dump_range("consciousnessData FULL", start_line2, start_line2 + 90)

idx3 = text.find('id="c2-list"')
if idx3 != -1:
    start_line3 = text[:idx3].count("\n") + 1
    dump_range("c2-list block", start_line3 - 5, start_line3 + 40)

idx4 = text.find("const metaphysicsData")
if idx4 != -1:
    start_line4 = text[:idx4].count("\n") + 1
    dump_range("metaphysicsData FULL", start_line4, start_line4 + 120)

Path("dump_everything_output.txt").write_text("\n".join(out), encoding="utf-8")
print("DONE - written to dump_everything_output.txt")
