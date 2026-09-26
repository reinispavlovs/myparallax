path = "index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
out = []
idx = content.find("Gunung Padang")
count = 0
while idx != -1:
    count += 1
    start = max(0, idx - 100)
    end = min(len(content), idx + 500)
    out.append(f"=== HIT {count} at pos {idx} ===")
    out.append(repr(content[start:end]))
    out.append("")
    idx = content.find("Gunung Padang", idx + 1)
out.append(f"Total hits: {count}")
with open("round8_gunungpadang_utf8.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
