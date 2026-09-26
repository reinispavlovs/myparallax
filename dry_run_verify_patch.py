from pathlib import Path

INDEX = Path("index.html")
text = INDEX.read_text(encoding="utf-8")

anchors = {
    "b1-body LV (telluric)": "milzigs vilnvads",
    "b1-body EN (telluric)": "global waveguide",
    "levitation desc1 LV": "Akustiska levitacija un virsmas vitrifikacija tika panakta",
    "levitation desc1 EN": "Acoustic levitation was achieved via frequency matching",
    "sheldrake b2": "Sheldrake",
    "3pillars b1 LV": "pjezoelektrisko kvarcu",
    "3pillars b1 EN": "quartz piezoelectric resonance",
    "3pillars b2 LV": "teta/gamma smadzenu stavokli",
    "3pillars b2 EN": "theta/gamma brain states",
    "3pillars b3 LV": "Pirmskataklizmas Standartizacija",
    "3pillars b3 EN": "Antediluvian Standardization",
    "mbody m2 LV": "strukturali identiski 27 pakapju meroga",
    "mbody m2 EN": "structurally identical across 27 orders of magnitude",
    "mbody m3 LV": "apziniba ir nelokala",
    "mbody m3 EN": "consciousness is non-local",
    "c-desc/c2body": "identical quantitative structural properties",
    "consciousness fundamental": "consciousness is non-local and fundamental",
    "flatline AWARE": "demonstrate accurate",
    "flatline refutes": "refutes reductionist materialism",
    "isomorphism identical density": "identical spatial density",
    "isomorphism scale invariance": "proving scale invariance",
    "c2-list identical matter": "Identical",
    "precession 25920": "25,920",
    "shining ones": "Shining Ones",
    "aware flatline eeg": "flatline EEG",
    "vazza feletti": "Vazza",
}

lines = []
lines.append("Total file length: " + str(len(text)) + " chars")
lines.append("")
lines.append("ANCHOR".ljust(40) + " COUNT".ljust(8) + "  STATUS")
lines.append("-" * 70)

for label, phrase in anchors.items():
    count = text.count(phrase)
    if count == 1:
        status = "OK (unique)"
    elif count > 1:
        status = "UNSAFE (ambiguous)"
    else:
        status = "MISSING"
    lines.append(label.ljust(40) + str(count).ljust(8) + "  " + status)

report = "\n".join(lines)
Path("patch_dry_run_report.txt").write_text(report, encoding="utf-8")
print("DONE - written to patch_dry_run_report.txt")
