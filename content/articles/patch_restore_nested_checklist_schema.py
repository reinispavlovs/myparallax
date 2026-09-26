"""
patch_restore_nested_checklist_schema.py

Restores a NEW nested "topics" tracking block in content/articles/topic_weights.json
for knowledge-gap / checklist-completion tracking.

IMPORTANT: This is a DIFFERENT namespace than the old orphaned schema removed in
patch_strip_nested_topic_weights.py (Task #65 / summary #110). The old schema used
topics.{id}.current_weight / weight_history and was read by nothing after the
digest_generator.py flat-schema patch (#107). That field name is intentionally
NOT reused here, to prevent digest_generator.py or promote_drafts.py from ever
accidentally reading this block as a weight source again.

New fields per topic (all initialized to 0 / 0% placeholders pending Task #153
compute_knowledge_gap_pct implementation):
    epistemic_class          (str: "A" | "B" | "C")
    potential_reclass_target (str | null)
    total_checklist_items    (int)
    completed_items          (int)
    missing_items            (int)
    percent_mapped           (float, 0-100)
    last_checklist_update    (ISO8601 str | null)

The existing flat top-level float keys ({topic_id}: float) used by
promote_drafts.py and digest_generator.py are left completely untouched.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent
WEIGHTS_PATH = REPO_ROOT / "content" / "articles" / "topic_weights.json"
HISTORY_DIR = REPO_ROOT / "digests" / "_history"

TOPIC_CONFIG = {
    "megalithic_engineering_acoustics": {
        "epistemic_class": "B",
        "potential_reclass_target": "A",
    },
    "cyclical_cataclysms_precession": {
        "epistemic_class": "C",
        "potential_reclass_target": None,
    },
    "consciousness_independence_nde": {
        "epistemic_class": "B",
        "potential_reclass_target": None,
    },
    "neural_cosmic_isomorphism": {
        "epistemic_class": "B",
        "potential_reclass_target": None,
    },
}

CHECKLIST_ITEM_COUNT = 6  # matches checklist_template in topic_checklists.json


def main():
    if not WEIGHTS_PATH.exists():
        print(f"[ERROR] {WEIGHTS_PATH} not found.")
        return

    raw = WEIGHTS_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)

    if "topics" in data:
        print("[ABORT] 'topics' key already exists in topic_weights.json.")
        print("        Refusing to overwrite. Inspect manually before proceeding.")
        return

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = HISTORY_DIR / f"topic_weights.json.bak.{ts}"
    shutil.copy2(WEIGHTS_PATH, backup_path)
    print(f"[OK] Backup created: {backup_path}")

    now_iso = datetime.now(timezone.utc).isoformat()

    topics_block = {}
    for topic_id, cfg in TOPIC_CONFIG.items():
        topics_block[topic_id] = {
            "epistemic_class": cfg["epistemic_class"],
            "potential_reclass_target": cfg["potential_reclass_target"],
            "total_checklist_items": CHECKLIST_ITEM_COUNT,
            "completed_items": 0,
            "missing_items": CHECKLIST_ITEM_COUNT,
            "percent_mapped": 0.0,
            "last_checklist_update": None,
        }

    data["topics"] = topics_block
    data["_topics_schema_note"] = (
        "This 'topics' block is a KNOWLEDGE-GAP tracker (checklist completion), "
        "NOT a weight-history schema. Flat top-level float keys remain the sole "
        "live weight values read by promote_drafts.py / digest_generator.py. "
        "percent_mapped is a placeholder (0%) pending Task #153 "
        "(compute_knowledge_gap_pct) implementation."
    )
    data["_topics_schema_added_at"] = now_iso

    WEIGHTS_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
        newline="",
    )
    print(f"[OK] Nested 'topics' checklist-tracking block added to {WEIGHTS_PATH}")
    print("[OK] Flat weight keys preserved untouched.")
    for topic_id in TOPIC_CONFIG:
        print(f"     - {topic_id}: percent_mapped=0.0 (placeholder)")


if __name__ == "__main__":
    main()