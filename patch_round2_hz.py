# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("index.html")
text = p.read_text(encoding="utf-8")

old = "'b1-body': 'Megaliths are anchored at geomagnetic nodes. Using quartz piezoelectric resonance in granite, signals were conducted through Earth\u2019s crust rather than air at ~7.83\u2013110 Hz.',"
new = "'b1-body': 'A fringe hypothesis proposes megaliths were positioned at geomagnetic nodes, theorizing that quartz\u2019s piezoelectric properties in granite could have facilitated signal transmission through Earth\u2019s crust rather than air. Note: the widely cited \u201c~7.83\u2013110 Hz\u201d range conflates the measured Schumann resonance (7.83 Hz) with a separately claimed, unverified 110 Hz phenomenon.',"

count = text.count(old)
print("Occurrences found: " + str(count))

if count == 1:
    backup = p.with_suffix(".html.bak_round2hz")
    backup.write_text(text, encoding="utf-8")
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print("[OK] b1-body EN -- replaced 1 occurrence")
elif count == 0:
    print("[MISSING] Anchor not found -- check for hidden character mismatch")
else:
    print("[UNSAFE] " + str(count) + " occurrences -- refusing to patch, need more context")

print("New file length: " + str(len(text)))
