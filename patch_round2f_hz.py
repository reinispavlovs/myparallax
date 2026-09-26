import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

old_lv = ("110 Hz frekvence stimul\u0113 teta smadze\u0146u "
          "vi\u013c\u0146us labaj\u0101 puslod\u0113, atsl\u0113dzot "
          "3D biolo\u0123iskos filtrus un veicinot "
          "\u0101rpus\u0137erme\u0146a uztveri (OBE).")

new_lv = ("Nepier\u0101d\u012bta hipot\u0113ze pie\u0146em, ka 110 Hz "
          "frekvence var\u0113tu ietekm\u0113t teta smadze\u0146u "
          "vi\u013c\u0146us labaj\u0101 puslod\u0113 un "
          "\u0101rpus\u0137erme\u0146a uztveri (OBE); \u0161is "
          "meh\u0101nisms zin\u0101tniski nav apstiprin\u0101ts.")

count = text.count(old_lv)
print(f"consciousnessData.metaphysics LV (correct anchor): found {count}")

backup = pathlib.Path("index.html.bak_round2fhz")
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

if count == 1:
    updated = text.replace(old_lv, new_lv)
    p.write_text(updated, encoding="utf-8")
    print("OK - replaced 1 (final hedge applied)")
else:
    idx = text.find(old_lv[:40])
    print(f"MISMATCH (found {count}, expected 1) - SKIPPED")
    print(f"Partial match index (first 40 chars): {idx}")
    if idx != -1:
        print("Context around partial match:")
        print(repr(text[max(0,idx-20):idx+200]))

print(f"Backup saved to: {backup}")