import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

anchors = [
    "Verified Perception",
    "Verified perception during cardiac arrest",
    "Verified visual and auditory perception during cardiac arrest",
    "verified out-of-body resuscitation phases",
    "verified out-of-body CPR phases",
    "verified out-of-body observations (OBE)",
    "build identically without orbital metal satellites",
    "evolve under identical self-organizing network dynamics",
    "apliecina, ka apzi\u0146a ir fundament\u0101la",
    "apliecina ie\u0161\u0113j\u0101s kameras",
    "p\u0113t\u012bjumi apliecina, ka vizu\u0101l\u0101"
]

report = ["=== ROUND 5 VERBATIM CONTEXT DUMP ===\n"]

for a in anchors:
    cnt = text.count(a)
    report.append(f"\n{'='*60}\nANCHOR: {a!r}\nCOUNT: {cnt}\n{'='*60}")
    start = 0
    idx = 1
    while True:
        pos = text.find(a, start)
        if pos == -1:
            break
        s = max(0, pos - 60)
        e = min(len(text), pos + len(a) + 200)
        report.append(f"\n--- Hit #{idx} at pos {pos} ---")
        report.append(repr(text[s:e]))
        idx += 1
        start = pos + len(a)

pathlib.Path("round5_verbatim_dump.txt").write_text("\n".join(report), encoding="utf-8")
print("Done - see round5_verbatim_dump.txt")