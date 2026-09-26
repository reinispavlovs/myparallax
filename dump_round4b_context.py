import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

markers = [
    ("gapDetailsData gap-i object", "'gap-i':"),
    ("gapDetailsData gap-i object (alt)", "gap-i: {"),
    ("isomorphism duplicate desc1 full", "structural comparison between human cerebellar"),
    ("b2 uncouples LV pair", "uncouples from"),
    ("b3 desc2 full", "modin\u0101tu cilv\u0113ci pirms"),
]

report = ["=== ROUND 4B FULL CONTEXT ===\n"]
for label, marker in markers:
    idx = text.find(marker)
    if idx == -1:
        report.append(f"\n--- {label} ('{marker}') NOT FOUND ---")
        continue
    start = max(0, idx - 500)
    end = min(len(text), idx + 700)
    report.append(f"\n--- {label} (pos {idx}) ---")
    report.append(text[start:end])

pathlib.Path("round4b_context_report.txt").write_text("\n".join(report), encoding="utf-8")
print("Done - see round4b_context_report.txt")