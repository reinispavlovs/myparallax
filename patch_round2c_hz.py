# -*- coding: utf-8 -*-
import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

old1 = "sign\u0101ls un ener\u0123ija teor\u0113tiski var\u0113ja tikt vad\u012bta nevis caur gaisu, bet caur Zemes ie\u017eu sl\u0101ni frekvenc\u0113 ~7.83\u2013110 Hz."
new1 = "tiek pie\u0146emts (bet nav pier\u0101d\u012bts), ka sign\u0101ls teor\u0113tiski var\u0113tu tikt vad\u012bts caur Zemes ie\u017eu sl\u0101ni. Piez\u012bme: bie\u017e\u0101 cit\u0101t\u0101 min\u0113tais diapazons \"~7.83\u2013110 Hz\" sajauc m\u0113r\u012bto \u0160\u016bma\u0146a rezonansi (7.83 Hz) ar atsevi\u0161\u0137i apgalvotu, nepier\u0101d\u012btu 110 Hz fenomenu."

old2 = "110\u2013111 Hz st\u0101vvi\u013c\u0146i gran\u012bta un ka\u013c\u0137akmens telp\u0101s ierosina pjezoelektrisko efektu kvarca krist\u0101los. Akustisk\u0101 levit\u0101cija un virsmas vitrifik\u0101cija tika pan\u0101kta ar frekven\u010du harmoniz\u0101ciju kimatiskajos mezglos."
new2 = "Margin\u0101la hipot\u0113ze apgalvo, ka 110\u2013111 Hz st\u0101vvi\u013c\u0146i gran\u012bta un ka\u013c\u0137akmens telp\u0101s var\u0113tu ierosin\u0101t pjezoelektrisko efektu kvarca krist\u0101los; apgalvot\u0101 akustisk\u0101 levit\u0101cija un virsmas vitrifik\u0101cija arheolo\u0123iski nav pier\u0101d\u012bta."

old3 = "Zeme darboj\u0101s k\u0101 milz\u012bgs vi\u013c\u0146vads: sign\u0101li un sp\u0113ks tika vad\u012bti caur ie\u017eu sl\u0101ni, izmantojot Zemes rezonansi (~7.83\u2013110 Hz), l\u012bdz\u012bgi k\u0101 m\u016bsdienu satel\u012bti izmanto radiovi\u013c\u0146us."
new3 = "Hipot\u0113ze paredz, ka Zeme var\u0113tu darboties k\u0101 vi\u013c\u0146vads: sign\u0101li un sp\u0113ks teor\u0113tiski tiktu vad\u012bti caur ie\u017eu sl\u0101ni. Piez\u012bme: \"~7.83\u2013110 Hz\" apvieno m\u0113r\u012bto \u0160\u016bma\u0146a rezonansi (7.83 Hz) ar nepier\u0101d\u012btu 110 Hz apgalvojumu; \u0161\u012b meh\u0101nika nav zin\u0101tniski apstiprin\u0101ta."

old4 = "110 Hz frekvence stimul\u0113 teta smadze\u0146u vi\u013c\u0146us labaj\u0101 puslod\u0113, atsl\u0113dzot 3D biolo\u0123iskos filtrus un veicinot \u0101rpusk\u0137erme\u0146a uztveri (OBE)."
new4 = "Nepier\u0101d\u012bta hipot\u0113ze pie\u0146em, ka 110 Hz akustisk\u0101 frekvence var\u0113tu mazin\u0101t kreis\u0101s puslodes dominanci un izrais\u012bt teta vi\u013c\u0146u smadze\u0146u st\u0101vok\u013cus, kas tiek saist\u012bti ar \u0101rpusk\u0137erme\u0146a uztveri (OBE); \u0161is c\u0113loniskais meh\u0101nisms nav zin\u0101tniski apstiprin\u0101ts."

replacements = [
    ("b1-body LV (x2)", old1, new1, 2),
    ("bridgeData.b1.desc1 LV", old2, new2, 1),
    ("bridgeData.b1.desc2 LV", old3, new3, 1),
    ("consciousnessData.metaphysics LV", old4, new4, 1),
]

bak = pathlib.Path("index.html.bak_round2chz")
bak.write_text(text, encoding="utf-8")

report = []
for label, old, new, expected in replacements:
    count = text.count(old)
    if count != expected:
        report.append(f"{label}: MISMATCH (found {count}, expected {expected}) - SKIPPED")
        continue
    text = text.replace(old, new)
    report.append(f"{label}: OK (replaced {count})")

p.write_text(text, encoding="utf-8")

with open("patch_round2c_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print("\n".join(report))
print("Backup saved to:", bak)
