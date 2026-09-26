path = "index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
print("Total length:", len(content))
print("Double quotes:", content.count(chr(34)))
print("Open braces:", content.count(chr(123)), "Close braces:", content.count(chr(125)))
print("Open parens:", content.count(chr(40)), "Close parens:", content.count(chr(41)))
mp = [chr(195), chr(226)+chr(8364), chr(196)+chr(8220), chr(197)+chr(161), chr(196)+chr(171)]
mh = sum(content.count(p) for p in mp)
print("Mojibake hits:", mh)
terms = ["fringe", "not accepted by mainstream", "pseudoscien", "nav pie" + chr(326) + "emts zin" + chr(257) + "tn" + chr(275)]
print("Residual asymmetry terms:")
for t in terms:
    c = content.lower().count(t.lower())
    print(t + ": " + str(c) + "x")
print("Done.")
