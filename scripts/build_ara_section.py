import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "content" / "articles" / "index.json"
TRIBUNAL_PATH = ROOT / "tribunal.html"

ARA_ORDER = [
    "consciousness_independence_nde",
    "megalithic_engineering_acoustics",
    "cyclical_cataclysms_precession",
]

def build_block(topic):
    score = topic.get("credibility_score", "N/A")
    risk = topic.get("risk_level", "UNKNOWN")
    article_file = topic.get("article_file", "")
    generated = topic.get("generated_at", "")[:10]
    return (
        '<p class="mb-2"><strong>Corpus Analysis Status:</strong> '
        f'Credibility Score {score} &middot; Risk Level: {risk} &middot; Updated {generated}</p>'
        f'<p><a href="content/articles/{article_file}" '
        'class="text-amber-400 hover:underline font-semibold">'
        'Read Full Statistical Breakdown &rarr;</a></p>'
    )

def main():
    index_data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    topics = index_data["topics"]
    html = TRIBUNAL_PATH.read_text(encoding="utf-8")

    pattern = re.compile(r'(<div class="ara-panel-inner">)(.*?)(</div>)', re.DOTALL)
    matches = list(pattern.finditer(html))

    if len(matches) < len(ARA_ORDER):
        raise RuntimeError(f"Expected {len(ARA_ORDER)} ara-panel-inner blocks, found {len(matches)}")

    new_html = html
    offset = 0
    for i, topic_id in enumerate(ARA_ORDER):
        if topic_id not in topics:
            print(f"[WARN] '{topic_id}' not in index.json, skipping.")
            continue
        block = build_block(topics[topic_id])
        m = matches[i]
        start, end = m.start(2) + offset, m.end(2) + offset
        new_html = new_html[:start] + block + new_html[end:]
        offset += len(block) - (end - start)

    TRIBUNAL_PATH.write_text(new_html, encoding="utf-8")
    print(f"[OK] Injected {len(ARA_ORDER)} ARA sections into tribunal.html")

if __name__ == "__main__":
    main()
