import json
from pathlib import Path

REPO_ROOT = Path(".").resolve()
CHECKLIST_PATH = REPO_ROOT / "content" / "articles" / "topic_checklists.json"

if not CHECKLIST_PATH.exists():
    print(f"[ERROR] File not found: {CHECKLIST_PATH}")
    raise SystemExit(1)

data = json.loads(CHECKLIST_PATH.read_text(encoding="utf-8"))

TARGET_TOPICS = ["megalithic_engineering_acoustics", "cyclical_cataclysms_precession"]

topics_block = data.get("topics", data)  # handle either {"topics": {...}} or flat {...}

for topic_id in TARGET_TOPICS:
    print("=" * 70)
    print(f"TOPIC: {topic_id}")
    print("=" * 70)
    topic_entry = topics_block.get(topic_id)
    if topic_entry is None:
        print("  [MISSING] No entry found for this topic_id.")
        continue

    items = topic_entry.get("items", [])
    if not items:
        print("  [WARN] 'items' list is empty or missing.")
        print("  Raw entry keys:", list(topic_entry.keys()))
        continue

    for idx, item in enumerate(items, start=1):
        name = item.get("name") or item.get("item") or item.get("id") or f"item_{idx}"
        status = item.get("status", "UNKNOWN")
        note = item.get("note") or item.get("description") or item.get("notes") or ""
        flag_marker = "  <<< FLAGGED_CONFLICT" if status == "flagged_conflict" else ""
        print(f"  [{idx}] {name}")
        print(f"      status : {status}{flag_marker}")
        if note:
            print(f"      note   : {note}")
        print()

print("=" * 70)
print("[DONE] Inspect the FLAGGED_CONFLICT item(s) above before editing.")
