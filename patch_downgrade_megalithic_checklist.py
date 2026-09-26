import json
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(".").resolve()
CHECKLIST_PATH = REPO_ROOT / "content" / "articles" / "topic_checklists.json"

data = json.loads(CHECKLIST_PATH.read_text(encoding="utf-8"))
topics_block = data.get("topics", data)

topic_id = "megalithic_engineering_acoustics"
topic_entry = topics_block[topic_id]
items = topic_entry["items"]

changed = False
for item in items:
    name = item.get("name") or item.get("item") or item.get("id")
    if name == "causal_mechanism" and item.get("status") == "flagged_conflict":
        item["status"] = "partial"
        item["note"] = (
            "Downgraded from flagged_conflict on 2026-09-23. Frontend "
            "(megaliths-cosmology.html) piezoelectric/psychoacoustic claims "
            "relabeled as speculative/unverified hypothesis "
            "(patch_fix_piezoelectric_hedging.py). No peer-reviewed causal "
            "mechanism established; illustrative acoustic resonance model "
            "remains hypothesis-only."
        )
        changed = True

if not changed:
    print("[WARN] No flagged_conflict causal_mechanism item found. No changes made.")
    raise SystemExit(0)

backup_path = CHECKLIST_PATH.with_name(
    f"topic_checklists.json.bak.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
)
backup_path.write_text(CHECKLIST_PATH.read_text(encoding="utf-8"), encoding="utf-8")
CHECKLIST_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"[OK] causal_mechanism -> 'partial' for {topic_id}")
print(f"[OK] Backup saved: {backup_path.name}")
