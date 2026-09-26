import pathlib, shutil

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

backup = pathlib.Path("index.html.bak_round4c")
if not backup.exists():
    shutil.copy(p, backup)

pairs = [
    ("gap-i.known LV",
     "Kvantitat\u012bvi identisks spektr\u0101lais jaudas bl\u012bvums un mezglu savienojam\u012bba (4.6\u20135.4) starp cilv\u0113ka smadzen\u012bt\u0113m un galaktiku kosmisko t\u012bklu $10^{27}$ m\u0113rog\u0101.",
     "Kvantitat\u012bvi statistiski l\u012bdz\u012bgs spektr\u0101lais jaudas bl\u012bvums un mezglu savienojam\u012bba (4.6\u20135.4) starp cilv\u0113ka smadzen\u012bt\u0113m un galaktiku kosmisko t\u012bklu $10^{27}$ m\u0113rog\u0101 (neapstiprin\u0101ta korel\u0101cija, ne pier\u0101d\u012bjums)."),

    ("gap-i.known EN",
     "Quantitatively identical spatial power spectral density and node degree (4.6\u20135.4) between human cerebellum and galaxy web across 27 orders of magnitude.",
     "Quantitatively similar spatial power spectral density and node degree (4.6\u20135.4) between human cerebellum and galaxy web across 27 orders of magnitude (an unconfirmed correlation, not proof of a causal link)."),

    ("isomorphism.desc1 LV tail",
     "atkl\u0101ja identisku spektr\u0101lo jaudas bl\u012bvumu.",
     "atkl\u0101ja statistiski l\u012bdz\u012bgu spektr\u0101lo jaudas bl\u012bvuma modeli (neapstiprin\u0101ta korel\u0101cija)."),

    ("isomorphism.desc1 EN tail",
     "revealed identical spatial density across 27 orders of magnitude.",
     "revealed a statistically similar spatial density pattern across 27 orders of magnitude (an unconfirmed correlation, not evidence of a causal link)."),

    ("isomorphism.desc2 LV",
     "apstiprinot frakt\u0101lo herm\u0113tisko aksiomu: 'K\u0101 aug\u0161\u0101, t\u0101 apak\u0161\u0101'.",
     "kas da\u017ei p\u0113tnieki interpret\u0113 k\u0101 iesp\u0113jamu atbalstu sen\u0101jai hermetiskai id\u0113jai 'K\u0101 aug\u0161\u0101, t\u0101 apak\u0161\u0101' \u2013 \u0161\u012b sakar\u012ba paliek spekulat\u012bva un nepier\u0101d\u012bta."),

    ("isomorphism.desc2 EN",
     "proving scale invariance and Alan Watts' unified observer framework.",
     "which some researchers interpret as suggestive of scale-invariant patterns \u2013 an intriguing but unproven and speculative parallel, not a demonstrated causal or ontological link."),

    ("b2.desc1 LV",
     "R\u016bperta \u0160eldreika morfo\u0123en\u0113tiskais lauks apliecina: kad prasme tiek apg\u016bta vien\u0101 viet\u0101, t\u0101 k\u013c\u016bst pieejama visai sugai.",
     "R\u016bperta \u0160eldreika margin\u0101l\u0101 morfo\u0123en\u0113tisk\u0101 lauka hipot\u0113ze (netiek atz\u012bta akad\u0113misk\u0101j\u0101 zin\u0101tn\u0113) paredz, ka kad prasme tiek apg\u016bta vien\u0101 viet\u0101, t\u0101 var\u0113tu k\u013c\u016bt pieejama visai sugai."),

    ("b2.desc1 EN",
     "Rupert Sheldrake's morphogenetic field confirms non-local information transfer across species without physical contact.",
     "Rupert Sheldrake's fringe morphogenetic field hypothesis (not accepted by mainstream science) proposes non-local information transfer across species without physical contact."),

    ("b2.desc2 EN tail",
     "identical to clinical NDE",
     "conceptually similar to descriptions in clinical NDE reports (an unconfirmed parallel)"),
]

report = ["=== ROUND 4C PATCH REPORT ===\n"]
applied = 0
for label, old, new in pairs:
    c = text.count(old)
    if c == 0:
        report.append(f"[MISSING] {label} -- anchor not found")
    elif c > 2:
        report.append(f"[UNSAFE] {label} -- found {c} times, skipping")
    else:
        text = text.replace(old, new)
        report.append(f"[OK] {label} -- replaced {c}x")
        applied += c

pathlib.Path("index.html").write_text(text, encoding="utf-8")
report.append(f"\nTotal replacements applied: {applied}")
report.append(f"New file length: {len(text)}")
pathlib.Path("round4c_patch_report.txt").write_text("\n".join(report), encoding="utf-8")
print("Done - see round4c_patch_report.txt")