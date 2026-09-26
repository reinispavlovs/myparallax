import pathlib

p = pathlib.Path("index.html")
text = p.read_text(encoding="utf-8")

idx = text.find("uncouples from")
start = max(0, idx - 1200)
end = min(len(text), idx + 100)

report = ["=== B2 FULL BLOCK CONTEXT ===\n"]
report.append(text[start:end])

pathlib.Path("round4c_b2_context.txt").write_text("\n".join(report), encoding="utf-8")
print("Done - see round4c_b2_context.txt")