import pathlib, re

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

terms = ["verified", "verific\u0113ts", "proven", "pier\u0101d\u012bts",
         "confirmed", "apstiprin\u0101ts", "identical", "apliecina"]

report = ["=== ROUND 4 FINAL CONTEXT DUMP ===\n"]

for t in terms:
    report.append(f"\n{'='*60}\nTERM: '{t}'\n{'='*60}")
    lower_text = text.lower()
    lower_t = t.lower()
    start = 0
    idx = 1
    while True:
        pos = lower_text.find(lower_t, start)
        if pos == -1:
            break
        s = max(0, pos - 100)
        e = min(len(text), pos + len(t) + 100)
        snippet = text[s:e].replace("\n", " \\n ")
        report.append(f"\n--- Hit #{idx} at pos {pos} ---")
        report.append(snippet)
        idx += 1
        start = pos + len(t)

pathlib.Path("round4_final_context_dump.txt").write_text("\n".join(report), encoding="utf-8")
print("Done - see round4_final_context_dump.txt")