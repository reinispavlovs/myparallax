import pathlib

p = pathlib.Path("index.html")
raw = p.read_bytes()

anchor = b"110 Hz frekvence"
idx = raw.find(anchor)

lines = []
lines.append(f"anchor byte index: {idx}")

if idx != -1:
    start = max(0, idx - 50)
    end = idx + 400
    chunk = raw[start:end]
    lines.append("HEX:")
    lines.append(chunk.hex())
    lines.append("")
    lines.append("LATIN1 DECODE (1:1 byte-to-codepoint mapping, never fails):")
    lines.append(chunk.decode("latin-1"))
    lines.append("")
    try:
        utf8_decoded = chunk.decode("utf-8")
        lines.append("UTF-8 DECODE (succeeded):")
        lines.append(utf8_decoded)
    except UnicodeDecodeError as e:
        lines.append(f"UTF-8 DECODE FAILED: {e}")
else:
    lines.append("Anchor not found in raw bytes")

report = "\n".join(lines)
pathlib.Path("round2e_hexdump_report.txt").write_text(report, encoding="utf-8")
print("Report written to round2e_hexdump_report.txt")
print(f"Report length: {len(report)}")