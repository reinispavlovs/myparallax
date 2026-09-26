import json
from pathlib import Path

REPO_ROOT = Path(".").resolve()
INDEX_PATH = REPO_ROOT / "content" / "articles" / "index.json"
PROMOTED_DIR = REPO_ROOT / "drafts" / "_promoted"

index_data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
topics = index_data.get("topics", {})

print("=== index.json risk_level per topic ===")
for tid, entry in topics.items():
    print(f"{tid}: risk_level={entry.get('risk_level')!r}, credibility_score={entry.get('credibility_score')}, promoted_at={entry.get('promoted_at')}")

print()
print("=== drafts/_promoted/*.meta.json risk_level ===")
if PROMOTED_DIR.exists():
    for mf in sorted(PROMOTED_DIR.glob("*.meta.json")):
        meta = json.loads(mf.read_text(encoding="utf-8"))
        print(f"{mf.name}: topic_id={meta.get('topic_id')}, risk_level={meta.get('risk_level')!r}, promoted_at={meta.get('promoted_at')}")
else:
    print("PROMOTED_DIR does not exist:", PROMOTED_DIR)
