import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

report = ["=== ROUND 4 FINAL INTEGRITY + SWEEP CHECK ===\n"]
report.append(f"File length: {len(text)} chars")
report.append(f"Double quotes: {text.count(chr(34))}")
report.append(f"Curly braces: {{ {text.count('{')} / }} {text.count('}')}")
report.append(f"Parens: ( {text.count('(')} / ) {text.count(')')}")

# mojibake check
mojibake_markers = ["Ä", "Å", "Â", "â€", "Ð", "Ñ"]
mojibake_hits = sum(text.count(m) for m in mojibake_markers)
report.append(f"Mojibake marker hits: {mojibake_hits}")

# remaining overclaim terms sweep
terms = ["verified", "verific\u0113ts", "proven", "pier\u0101d\u012bts", "confirmed", "apstiprin\u0101ts",
          "identical", "identisks", "definitively", "defin\u012btīvi", "fact that", "fakts, ka",
          "proves that", "pier\u0101da, ka", "apliecina", "confirms"]

total_hits = 0
for t in terms:
    c = text.lower().count(t.lower())
    if c > 0:
        report.append(f"  '{t}': {c} hits")
        total_hits += c

report.append(f"\nTotal remaining overclaim-term hits: {total_hits}")

pathlib.Path("round4_final_check_report.txt").write_text("\n".join(report), encoding="utf-8")
print("Done - see round4_final_check_report.txt")