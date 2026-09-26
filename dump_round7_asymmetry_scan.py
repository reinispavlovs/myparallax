# -*- coding: utf-8 -*-
path = "index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

terms = [
    "not accepted by mainstream",
    "fringe hypothesis",
    "scientifically contested",
    "unverified hypothesis",
    "not scientifically accepted",
    "contested by mainstream",
    "lacks scientific support",
    "no scientific consensus",
    "mainstream science rejects",
    "mainstream researchers dispute",
    "nav pie\u0146emts zin\u0101tn\u0113",
    "maz\u0101ku atzin\u012bbu",
    "netiek atz\u012bts",
    "contested claim",
    "disputed by",
    "rejected by mainstream",
    "pseudoscien",
]

report_lines = []
lower_content = content.lower()

for term in terms:
    term_lower = term.lower()
    idx = 0
    count = 0
    while True:
        found = lower_content.find(term_lower, idx)
        if found == -1:
            break
        count += 1
        start = max(0, found - 180)
        end = min(len(content), found + len(term) + 220)
        window = content[start:end]
        report_lines.append("=== TERM: '" + term + "' | Occurrence #" + str(count) + " | Pos: " + str(found) + " ===")
        report_lines.append(window)
        report_lines.append("")
        idx = found + len(term)

report_lines.append("=== TOTAL SCAN COMPLETE ===")

with open("round7_asymmetry_scan.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))

print("Done. Wrote round7_asymmetry_scan.txt")
