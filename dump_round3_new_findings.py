import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

lines = []

# Wider context around the two new problem areas
for label, center in [("BLOCK_A_91488", 91488), ("BLOCK_B_98227", 98227)]:
    start = max(0, center - 500)
    end = min(len(text), center + 700)
    snippet = text[start:end]
    lines.append(f"=== {label} (pos {center}, window {start}-{end}) ===")
    lines.append(snippet)
    lines.append("\n" + "="*80 + "\n")

report = "\n".join(lines)
pathlib.Path("round3_new_findings_report.txt").write_text(report, encoding="utf-8")
print("Report written to round3_new_findings_report.txt")
print(f"Report length: {len(report)}")