path = "index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
idx = content.find("Gunung Padang")
count = 0
while idx != -1:
    count += 1
    print("=== HIT", count, "at pos", idx, "===")
    start = max(0, idx - 100)
    end = min(len(content), idx + 500)
    print(repr(content[start:end]))
    print()
    idx = content.find("Gunung Padang", idx + 1)
print("Total hits:", count)
