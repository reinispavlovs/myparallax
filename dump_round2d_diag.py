import pathlib

text = pathlib.Path("index.html").read_text(encoding="utf-8")

anchor = "110 Hz frekvence"
idx = text.find(anchor)

report_lines = []

if idx == -1:
    report_lines.append("ANCHOR NOT FOUND AT ALL: '110 Hz frekvence'")
else:
    report_lines.append(f"Found at index: {idx}")
    # grab a window before and after
    start = max(0, idx - 50)
    end = min(len(text), idx + 400)
    snippet = text[start:end]
    report_lines.append("RAW SNIPPET:")
    report_lines.append(snippet)
    report_lines.append("")
    report_lines.append("REPR SNIPPET:")
    report_lines.append(repr(snippet))

    # find ALL occurrences too
    all_idx = []
    pos = 0
    while True:
        i = text.find(anchor, pos)
        if i == -1:
            break
        all_idx.append(i)
        pos = i + 1
    report_lines.append("")
    report_lines.append(f"Total occurrences of anchor: {len(all_idx)}")
    report_lines.append(f"All indices: {all_idx}")

pathlib.Path("round2d_diag_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
print("Report written to round2d_diag_report.txt")