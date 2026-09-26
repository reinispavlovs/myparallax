import pathlib, re

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

markers = [
    ("gap-i known block", "gap-i-title"),
    ("isomorphism duplicate near cerebellar", "cerebellar neuronal networks"),
    ("bridgeData b3", "'b3': {" ),
    ("bridgeData b3 (alt quote style)", "b3: {"),
    ("uncouples consciousness", "uncouples from"),
]

report = ["=== ROUND 4 CONTEXT DUMP ===\n"]
for label, marker in markers:
    idx = text.find(marker)
    if idx == -1:
        report.append(f"\n--- {label} ('{marker}') NOT FOUND ---")
        continue
    start = max(0, idx - 100)
    end = min(len(text), idx + 900)
    report.append(f"\n--- {label} (pos {idx}) ---")
    report.append(text[start:end])

pathlib.Path("round4_context_report.txt").write_text("\n".join(report), encoding="utf-8")
print("Done - see round4_context_report.txt")