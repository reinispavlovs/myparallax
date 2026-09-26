import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")
orig_len = len(text)

replacements = [
    # (anchor, replacement, expected_count)
    ("Verified Perception", "Reported Perception", 3),
    ("Verified perception during cardiac arrest.",
     "Reported perception during cardiac arrest (contested).", 1),
    ("Verified visual and auditory perception during cardiac arrest",
     "Reported visual and auditory perception during cardiac arrest", 1),
    ("verified out-of-body resuscitation phases",
     "reported out-of-body resuscitation phases", 1),
    ("verified out-of-body CPR phases",
     "reported out-of-body CPR phases", 1),
    ("verified out-of-body observations (OBE)",
     "reported out-of-body observations (OBE)", 1),
    ("build identically without orbital metal satellites",
     "build with striking similarity, without orbital metal satellites", 1),
    ("evolve under identical self-organizing network dynamics",
     "evolve under structurally similar self-organizing network dynamics", 1),
    ("apliecina, ka apzi\u0146a ir fundament\u0101la",
     "liecina, ka apzi\u0146a var\u0113tu b\u016bt fundament\u0101la", 2),
    ("p\u0113t\u012bjumi apliecina, ka vizu\u0101l\u0101",
     "p\u0113t\u012bjumi liecina, ka vizu\u0101l\u0101", 1),
]

log = []
all_ok = True

for anchor, replacement, expected in replacements:
    actual = text.count(anchor)
    status = "OK" if actual == expected else "MISMATCH"
    if actual != expected:
        all_ok = False
    log.append(f"[{status}] anchor={anchor!r} expected={expected} actual={actual}")

if not all_ok:
    print("ABORTING - count mismatch detected:")
    for line in log:
        print(line)
else:
    for anchor, replacement, expected in replacements:
        text = text.replace(anchor, replacement)
    p.write_text(text, encoding="utf-8")
    print(f"SUCCESS - {len(replacements)} anchors replaced.")
    print(f"Length: {orig_len} -> {len(text)} (delta {len(text)-orig_len})")
    for line in log:
        print(line)