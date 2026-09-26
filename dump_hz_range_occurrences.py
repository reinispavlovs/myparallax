# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("index.html")
text = p.read_text(encoding="utf-8")

targets = ["7.83", "110 Hz", "7.83\u2013110", "7.83-110"]

lines = text.split("\n")
out = []
for i, line in enumerate(lines, start=1):
    for t in targets:
        if t in line:
            out.append(f"Line {i} | match='{t}' | {line.strip()[:200]}")
            break

report = "\n".join(out)
Path("hz_occurrences_report.txt").write_text(report, encoding="utf-8")
print(f"Total matching lines: {len(out)}")
print("Saved to hz_occurrences_report.txt")
