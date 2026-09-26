from pathlib import Path

text = Path("index.html").read_text(encoding="utf-8")
lines = text.splitlines()

def show(line_no, window=5):
    start = max(0, line_no - 1 - window)
    end = min(len(lines), line_no - 1 + window + 1)
    out = []
    for i in range(start, end):
        out.append(f"{i+1}: {lines[i]}")
    return "\n".join(out)

report = []
report.append("=== b1-body LV full (around line 716) ===")
report.append(show(716, window=2))
report.append("")
report.append("=== bridgeData b1 desc2 area (around line 1282) ===")
report.append(show(1282, window=6))

Path("round2b_missing_report.txt").write_text("\n".join(report), encoding="utf-8")
print("Saved to round2b_missing_report.txt")
