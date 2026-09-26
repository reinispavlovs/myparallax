import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

print(f"Total length: {len(text)}")
print(f"Quotes: {text.count(chr(34))}")
print(f"Braces: open={text.count(chr(123))} close={text.count(chr(125))}")
print(f"Parens: open={text.count(chr(40))} close={text.count(chr(41))}")

# Search for Gunung Padang dating claims
import re
for kw in ["Gunung Padang", "16,000", "16000", "25,000", "25000", "16 000", "25 000", "20,000", "20000"]:
    idx = text.find(kw)
    if idx != -1:
        s = max(0, idx-100)
        e = min(len(text), idx+250)
        print(f"\n--- Found '{kw}' at pos {idx} ---")
        print(repr(text[s:e]))

# Broad sweep round 5 verification
terms = ["verified", "proven", "confirmed", "identical", "definitively", "fact that", "proves that", "apliecina"]
print("\n\n=== REMAINING OVERCLAIM TERM COUNTS ===")
for t in terms:
    c_lower = text.lower().count(t.lower())
    print(f"{t}: {c_lower}")