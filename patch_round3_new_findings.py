import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")
original_len = len(text)

replacements = [
    (
        "BLOCK_A LV (structuresData.metaphysics)",
        "Piezoelektriskais kvarcs andes\u012bt\u0101 rada sp\u0113c\u012bgas elektromagn\u0113tisk\u0101 lauka anom\u0101lijas, stimul\u0113jot epif\u012bzi un telpas uztveri.",
        "Nepier\u0101d\u012bta hipot\u0113ze apgalvo, ka piezoelektriskais kvarcs andes\u012bt\u0101 var\u0113tu rad\u012bt elektromagn\u0113tisk\u0101 lauka anom\u0101lijas, kas teor\u0113tiski stimul\u0113tu epif\u012bzi un telpas uztveri; \u0161is meh\u0101nisms nav zin\u0101tniski pier\u0101d\u012bts.",
        1
    ),
    (
        "BLOCK_A EN (structuresData.metaphysics)",
        "Piezoelectric quartz composition creates localized electromagnetic anomalies stimulating the pineal gland and spatial perception.",
        "An unverified hypothesis suggests that piezoelectric quartz in andesite could create electromagnetic field anomalies theorized to stimulate the pineal gland and spatial perception; this mechanism remains scientifically unproven.",
        1
    ),
    (
        "BLOCK_B LV (gapDetailsData.gap-m.known)",
        "Verific\u0113ta 110\u2013121 Hz st\u0101vvi\u013c\u0146u rezonanse G\u012bzas Kara\u013ca kamer\u0101, \u0126al Saflieni hipogej\u0101 un Barabar gran\u012bta al\u0101s. Pjezoelektriskais kvarca efekts gran\u012bt\u0101 un andes\u012bt\u0101.",
        "M\u0113r\u012bta 110\u2013121 Hz st\u0101vvi\u013c\u0146u akustisk\u0101 rezonanse G\u012bzas Kara\u013ca kamer\u0101, \u0126al Saflieni hipogej\u0101 un Barabar gran\u012bta al\u0101s; pjezoelektriskais efekts gran\u012bt\u0101 un andes\u012bt\u0101 ir neapstiprin\u0101ta hipot\u0113ze.",
        1
    ),
    (
        "BLOCK_B EN (gapDetailsData.gap-m.known)",
        "Verified 110\u2013121 Hz standing wave acoustic resonance in Giza King's Chamber, Malta Hypogeum, and Barabar caves. Piezoelectric quartz mechanics mapped.",
        "Measured 110\u2013121 Hz standing wave acoustic resonance in Giza King's Chamber, Malta Hypogeum, and Barabar caves; piezoelectric quartz mechanics remain an unverified hypothesis.",
        1
    ),
]

report_lines = []
report_lines.append("=== ROUND 3 PATCH REPORT ===\n")

# Safety check pass first
all_safe = True
for label, anchor, hedge, expected in replacements:
    found = text.count(anchor)
    status = "OK" if found == expected else ("MISSING" if found == 0 else "UNSAFE-MULTI")
    if status != "OK":
        all_safe = False
    report_lines.append(f"[{status}] {label}: found={found} expected={expected}")

report_lines.append("")

if not all_safe:
    report_lines.append("ABORTED: Not all anchors matched expected count. No changes written.")
    pathlib.Path("round3_patch_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    print("ABORTED - see round3_patch_report.txt")
else:
    backup_path = pathlib.Path("index.html.bak_round3")
    backup_path.write_text(text, encoding="utf-8")
    report_lines.append(f"Backup written to {backup_path}")

    for label, anchor, hedge, expected in replacements:
        count_before = text.count(anchor)
        text = text.replace(anchor, hedge)
        report_lines.append(f"Applied: {label} (replaced {count_before} instance(s))")

    new_len = len(text)
    p.write_text(text, encoding="utf-8")
    report_lines.append(f"\nOriginal length: {original_len}")
    report_lines.append(f"New length: {new_len}")
    report_lines.append(f"Delta: {new_len - original_len}")
    report_lines.append("\nSUCCESS: index.html patched and saved.")
    pathlib.Path("round3_patch_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    print("SUCCESS - see round3_patch_report.txt")