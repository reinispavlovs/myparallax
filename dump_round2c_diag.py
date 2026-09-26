import re

with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

lines = text.split("\n")

def dump_window(keyword, label, window=250):
    out = []
    for i, line in enumerate(lines):
        if keyword in line:
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            context = "\n".join(lines[start:end])
            out.append(f"--- {label} match at line {i+1} ---")
            out.append(repr(context))
            out.append("")
    return out

report = []
report += dump_window("pjezo", "PIEZO (LV)")
report += dump_window("110", "110-mention")
report += dump_window("apzi", "CONSCIOUSNESS (LV apziņa)")

with open("round2c_diag_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print("Saved to round2c_diag_report.txt")
print("Total blocks found:", len(report) // 3)
