# -*- coding: utf-8 -*-
import shutil

path = "index.html"
backup = "index_backup_before_round7.html"
shutil.copy(path, backup)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

replacements = [
    (
        "A fringe hypothesis proposes megaliths were positioned",
        "An alternative hypothesis proposes megaliths were positioned"
    ),
    (
        "Proponents of this fringe hypothesis claim that in acoustic resonance chambers",
        "Proponents of this alternative hypothesis claim that in acoustic resonance chambers"
    ),
    (
        "A fringe hypothesis proposes that 110\u2013111 Hz standing waves",
        "An alternative hypothesis proposes that 110\u2013111 Hz standing waves"
    ),
    (
        "Rupert Sheldrake's fringe morphogenetic field hypothesis (not accepted by mainstream science) proposes",
        "Rupert Sheldrake's morphogenetic field hypothesis (an alternative model outside current mainstream neuroscience) proposes"
    ),
]

report = []
success_count = 0

for old, new in replacements:
    c = content.count(old)
    if c == 1:
        content = content.replace(old, new)
        success_count += 1
        report.append(f"OK ({c}x): {old[:60]}...")
    else:
        report.append(f"SKIP (found {c}x, expected 1): {old[:60]}...")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Done. {success_count}/{len(replacements)} replacements applied.")
print(f"New length: {len(content)}")
for line in report:
    print(line)
