import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")
original_len = len(text)

replacements = [
    ("c1-list LV (Parnia)",
     "Verific\u0113ta uztvere sirds mas\u0101\u017eas laik\u0101.",
     "Dokument\u0113ta uztvere sirds mas\u0101\u017eas laik\u0101 (nav pilnb\u0101r\u012bgi izsl\u0113gti alternat\u012bvi paskaidrojumi).",
     2),
    ("c2-list-item1 LV (spectral density)",
     "Identisks mat\u0113rijas sadal\u012bjums.",
     "Statistiski l\u012bdz\u012bgs mat\u0113rijas sadal\u012bjums.",
     2),
    ("c2-list-item2 LV (connection count)",
     "Identisks savienojumu skaits (4.6 l\u012bdz 5.4).",
     "Salist\u0101ms savienojumu skaits (4.6 l\u012bdz 5.4).",
     2),
]

report = ["=== ROUND 4 PATCH REPORT ===\n"]
all_safe = True
for label, anchor, hedge, expected in replacements:
    found = text.count(anchor)
    status = "OK" if found == expected else ("MISSING" if found == 0 else "UNSAFE-MULTI")
    if status != "OK":
        all_safe = False
    report.append(f"[{status}] {label}: found={found} expected={expected}")

report.append("")
if not all_safe:
    report.append("ABORTED: mismatch detected. No changes written.")
    pathlib.Path("round4_patch_report.txt").write_text("\n".join(report), encoding="utf-8")
    print("ABORTED - see round4_patch_report.txt")
else:
    pathlib.Path("index.html.bak_round4").write_text(text, encoding="utf-8")
    for label, anchor, hedge, expected in replacements:
        text = text.replace(anchor, hedge)
        report.append(f"Applied: {label}")
    p.write_text(text, encoding="utf-8")
    report.append(f"\nOriginal length: {original_len}")
    report.append(f"New length: {len(text)}")
    pathlib.Path("round4_patch_report.txt").write_text("\n".join(report), encoding="utf-8")
    print("SUCCESS - see round4_patch_report.txt")