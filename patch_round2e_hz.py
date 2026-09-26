import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

corrupted_old = "110 Hz frekvence stimul\u00c4\u201c teta smadze\u00c5\u2020u vi\u00c4\u00bc\u00c5\u2020us labaj\u00c4\u0081 puslod\u00c4\u201c, atsl\u00c4\u201cdzot 3D biolo\u00c4\u00a3iskos filtrus un veicinot \u00c4\u0081rpus\u00c4\u00b7erme\u00c5\u2020a uztveri (OBE)."

new_lv = "Nepier\u0101d\u012bta hipot\u0113ze pie\u0146em, ka 110 Hz frekvence var\u0113tu ietekm\u0113t teta smadze\u0146u vi\u013c\u0146us labaj\u0101 puslod\u0113 un \u0101rpus\u0137erme\u0146a uztveri (OBE); \u0161is meh\u0101nisms zin\u0101tniski nav apstiprin\u0101ts."

count = text.count(corrupted_old)
print(f"consciousnessData.metaphysics LV (mojibake anchor): found {count}")

backup = pathlib.Path("index.html.bak_round2ehz")
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

if count == 1:
    updated = text.replace(corrupted_old, new_lv)
    p.write_text(updated, encoding="utf-8")
    print("OK - replaced 1 (mojibake fixed + hedged)")
else:
    idx = text.find(corrupted_old[:30])
    print(f"MISMATCH (found {count}, expected 1) - SKIPPED")
    print(f"Partial match index (first 30 chars): {idx}")

print(f"Backup saved to: {backup}")