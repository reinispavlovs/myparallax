import pathlib
import re

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

lines = []
lines.append("=== FINAL HEDGE AUDIT ===\n")

# 1. Find all remaining "110 Hz" occurrences with context
lines.append("--- All '110 Hz' occurrences ---")
for m in re.finditer(r"110 Hz", text):
    start = max(0, m.start() - 60)
    end = min(len(text), m.end() + 100)
    snippet = text[start:end].replace("\n", " ")
    lines.append(f"[pos {m.start()}] ...{snippet}...")
lines.append("")

# 2. Find all "piezoelectric" / "pjezo" occurrences with context
lines.append("--- All piezoelectric/pjezo occurrences ---")
for m in re.finditer(r"(?i)piezo|pjezo", text):
    start = max(0, m.start() - 60)
    end = min(len(text), m.end() + 100)
    snippet = text[start:end].replace("\n", " ")
    lines.append(f"[pos {m.start()}] ...{snippet}...")
lines.append("")

# 3. Basic integrity checks
lines.append("--- Integrity checks ---")
lines.append(f"Total length: {len(text)} chars")
lines.append(f"Double-quote count: {text.count(chr(34))} (should be even)")
lines.append(f"Open braces {{: {text.count('{')}")
lines.append(f"Close braces }}: {text.count('}')}")
lines.append(f"Open parens (: {text.count('(')}")
lines.append(f"Close parens ): {text.count(')')}")

# 4. Try to find any leftover mojibake patterns (Ã, Â, Å as suspicious sequences)
suspicious = re.findall(r"[ÃÂÅ][^\s]{0,3}", text)
lines.append(f"\nSuspicious mojibake-like sequences found: {len(suspicious)}")
if suspicious:
    lines.append(str(suspicious[:30]))

report = "\n".join(lines)
pathlib.Path("final_hedge_audit_report.txt").write_text(report, encoding="utf-8")
print("Report written to final_hedge_audit_report.txt")
print(f"Report length: {len(report)}")