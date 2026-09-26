import pathlib, re

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

# Broad sweep for overclaim language not yet checked
terms = [
    "verified", "verific",       # EN + LV verific─ta
    "proven", "pier─d─ta",       # will show mojibake if present, that's fine for detection
    "confirmed", "apstiprin",
    "identical", "identisk",
    "definitively", "neapstr─d─mi",
    "fact that", "fakts, ka",
    "proves that", "pier─da, ka",
]

report = ["=== ROUND 4 BROAD OVERCLAIM SWEEP ===\n"]
total_hits = 0
for term in terms:
    idxs = [m.start() for m in re.finditer(re.escape(term), text, re.IGNORECASE)]
    if idxs:
        total_hits += len(idxs)
        report.append(f"\n--- '{term}' : {len(idxs)} hit(s) ---")
        for i in idxs[:10]:
            start = max(0, i-80)
            end = min(len(text), i+120)
            report.append(f"[pos {i}] ...{text[start:end]}...")

report.append(f"\n\nTOTAL HITS ACROSS ALL TERMS: {total_hits}")
pathlib.Path("round4_broad_sweep_report.txt").write_text("\n".join(report), encoding="utf-8")
print(f"Report written. Total hits: {total_hits}")