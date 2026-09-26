path = "index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
idx = content.find("Gunung Padang")
start = max(0, idx - 50)
end = min(len(content), idx + 1400)
with open("round8_full_utf8.txt", "w", encoding="utf-8") as f:
    f.write(repr(content[start:end]))
