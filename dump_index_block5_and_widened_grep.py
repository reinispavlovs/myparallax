import re
from pathlib import Path

ROOT = Path(".").resolve()
p = ROOT / "index.html"
text = p.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()

print("=" * 70)
print("STEP A: Map metaphysics Block 5 to site name")
print("=" * 70)
name_matches = list(re.finditer(r'name:\s*\{\s*LV:\s*"([^"]*)",\s*EN:\s*"([^"]*)"', text))
meta_matches = list(re.finditer(r'metaphysics:\s*\{', text))
for i, (nm, mm) in enumerate(zip(name_matches, meta_matches), 1):
    if i in (1, 5):
        print(f"Site {i}: EN name = {nm.group(2)}  (metaphysics at char {mm.start()})")

print()
print("=" * 70)
print("STEP B: Full case-insensitive grep for 'piezoelectric' and 'pineal'")
print("=" * 70)
for i, line in enumerate(lines, 1):
    if re.search(r"piezoelectric|pineal", line, re.IGNORECASE):
        print(f"Line {i}: {line.strip()[:160]}")

print()
print("=" * 70)
print("STEP C: Widened risk grep (stimulating|activat|creates.*anomal|entrain)")
print("=" * 70)
wide_pattern = re.compile(r"(stimulating|activat\w*|creates?\s+\w*\s*anomal\w*|entrain\w*)", re.IGNORECASE)
for i, line in enumerate(lines, 1):
    if wide_pattern.search(line):
        print(f"Line {i}: {line.strip()[:160]}")

print()
print("=" * 70)
print("STEP D: Locate LV versions of m1-body/m2-body/m3-body with line numbers")
print("=" * 70)
for key in ["m1-body", "m2-body", "m3-body"]:
    for m in re.finditer(rf"'{re.escape(key)}':\s*[\"'](.+?)[\"'],?\s*\n", text, re.DOTALL):
        line_no = text[:m.start()].count("\n") + 1
        print(f"Line {line_no}: {key} = {m.group(1)[:160]}")
print("DONE")
