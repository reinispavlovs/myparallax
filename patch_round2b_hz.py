import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")
orig_len = len(text)

report = []

def do_replace(name, old, new, expected):
    global text
    count = text.count(old)
    if count == expected:
        text = text.replace(old, new)
        report.append(f"OK   [{name}] replaced {count}x")
    elif count == 0:
        report.append(f"MISSING [{name}] anchor not found")
    else:
        report.append(f"UNEXPECTED_COUNT [{name}] found {count}, expected {expected}")

# TARGET 1: b1-body LV (occurs 2x: HTML + JS)
do_replace(
    "b1-body LV",
    "sl\u0101ni frekvenc\u0113 ~7.83\u2013110 Hz.",
    "sl\u0101ni. Piez\u012bme: pla\u0161i cit\u0113tais diapazons \"~7.83\u2013110 Hz\" apvieno verific\u0113to \u0160\u016bma\u0146a rezonansi (7.83 Hz) ar atsevi\u0161\u0137i apgalvotu, nep\u0101rbaud\u012btu 110 Hz efektu.",
    2
)

# TARGET 2: bridgeData.b1.desc1 LV (occurs 1x)
do_replace(
    "desc1 LV",
    "110\u2013111 Hz st\u0101vvi\u013c\u0146i gran\u012bta un ka\u013c\u0137akmens telp\u0101s ierosina pjezoelektrisko efektu kvarca krist\u0101los. Akustisk\u0101 levit\u0101cija un virsmas vitrifik\u0101cija tika pan\u0101kta ar frekven\u010du harmoniz\u0101ciju kimatiskajos mezglos.",
    "Margin\u0101la hipot\u0113ze apgalvo, ka 110\u2013111 Hz st\u0101vvi\u013c\u0146i gran\u012bta un ka\u013c\u0137akmens telp\u0101s var\u0113tu ierosin\u0101t pjezoelektrisku efektu kvarca krist\u0101los; apgalvot\u0101 akustisk\u0101 levit\u0101cija un virsmas vitrifik\u0101cija ar frekven\u010du harmoniz\u0101ciju nav pier\u0101d\u012bta.",
    1
)

# TARGET 3: bridgeData.b1.desc2 LV (occurs 1x)
do_replace(
    "desc2 LV",
    "izmantojot Zemes rezonansi (~7.83\u2013110 Hz),",
    "izmantojot Zemes rezonansi; piez\u012bme: bie\u017ei cit\u0113tais diapazons \"~7.83\u2013110 Hz\" apvieno \u0160\u016bma\u0146a rezonansi (7.83 Hz) ar atsevi\u0161\u0137i apgalvotu, nep\u0101rbaud\u012btu 110 Hz efektu,",
    1
)

# TARGET 4: consciousnessData/metaphysics LV (occurs 1x)
do_replace(
    "consciousnessData LV",
    "110 Hz frekvence stimul\u0113 teta smadze\u0146u vi\u013c\u0146us labaj\u0101 puslod\u0113, atsl\u0113dzot 3D biolo\u0123iskos filtrus un veicinot \u0101rpusk\u0137erme\u0146a uztveri (OBE).",
    "Nep\u0101rbaud\u012bta hipot\u0113ze apgalvo, ka 110 Hz akustisk\u0101 frekvence var\u0113tu nom\u0101kt kreis\u0101s puslodes dominanti un izrais\u012bt teta vi\u013c\u0146u smadze\u0146u st\u0101vok\u013cus, kas saist\u012bti ar \u0101rpusk\u0137erme\u0146a pieredz\u0113m (OBE); \u0161is c\u0113lo\u0146sakar\u012bbas meh\u0101nisms nav zin\u0101tniski pier\u0101d\u012bts.",
    1
)

if len(text) != orig_len:
    backup = pathlib.Path("index.html.bak_round2chz")
    backup.write_text(pathlib.Path("index.html").read_text(encoding="utf-8"), encoding="utf-8")
    p.write_text(text, encoding="utf-8")

pathlib.Path("patch_round2c_report.txt").write_text("\n".join(report), encoding="utf-8")
print("\n".join(report))
print("Done. New length:", len(text), "Old length:", orig_len)
