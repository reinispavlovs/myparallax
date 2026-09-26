import pathlib

p = pathlib.Path("index.html")
original = p.read_text(encoding="utf-8")

old = ("110 Hz frekvence stimul\u0113 teta smadze\u0146u vi\u013c\u0146us "
       "labaj\u0101 puslod\u0113, atsl\u0113dzot 3D biolo\u0123iskos filtrus "
       "un veicinot \u0101rpus\u0137ermen\u0146a uztveri (OBE).")

new = ("Nepier\u0101d\u012bta hipot\u0113ze pie\u0146em, ka 110 Hz frekvence "
       "var\u0113tu ietekm\u0113t teta smadze\u0146u vi\u013c\u0146us labaj\u0101 "
       "puslod\u0113 un \u0101rpus\u0137ermen\u0146a uztveri (OBE); \u0161is "
       "meh\u0101nisms zin\u0101tniski nav apstiprin\u0101ts.")

count = original.count(old)

backup = pathlib.Path("index.html.bak_round2dhz")
if not backup.exists():
    backup.write_text(original, encoding="utf-8")

if count == 1:
    updated = original.replace(old, new)
    p.write_text(updated, encoding="utf-8")
    print("consciousnessData.metaphysics LV: OK (replaced 1)")
else:
    print(f"consciousnessData.metaphysics LV: MISMATCH (found {count}, expected 1) - SKIPPED")

print(f"Backup saved to: {backup}")