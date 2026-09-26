"""
scripts/sync_checklist_percent.py

Reads content/articles/topic_checklists.json (qualitative SSOT),
computes percent_mapped per topic via compute_knowledge_gap_pct(),
and writes the result into a "topics" block inside
content/articles/topic_weights.json.

This is isolated from the live flat-weight schema used by
promote_drafts.py ({topic_id}: float). Nothing under "topics"
is read by the promotion/scoring pipeline yet (Task #153).

Usage:
    python scripts/sync_checklist_percent.py
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.shared.claim_layers_utils import compute_knowledge_gap_pct

CHECKLIST_PATH = REPO_ROOT / "content" / "articles" / "topic_checklists.json"
WEIGHTS_PATH = REPO_ROOT / "content" / "articles" / "topic_weights.json"
HISTORY_DIR = REPO_ROOT / "content" / "articles" / "_history"


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def backup_weights_file():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = HISTORY_DIR / f"topic_weights.json.bak.{ts}.json"
    shutil.copy2(WEIGHTS_PATH, dest)
    return dest


def main():
    if not CHECKLIST_PATH.exists():
        print(f"[ERROR] Checklist file not found: {CHECKLIST_PATH}")
        sys.exit(1)
    if not WEIGHTS_PATH.exists():
        print(f"[ERROR] Weights file not found: {WEIGHTS_PATH}")
        sys.exit(1)

    checklist_data = load_json(CHECKLIST_PATH)
    weights_data = load_json(WEIGHTS_PATH)

    checklist_topics = checklist_data.get("topics", {})
    if not checklist_topics:
        print("[ERROR] No 'topics' block found in topic_checklists.json")
        sys.exit(1)

    backup_path = backup_weights_file()
    print(f"[OK] Backed up topic_weights.json -> {backup_path}")

    results = []
    topics_block = weights_data.get("topics", {})

    for topic_id, topic_def in checklist_topics.items():
        items = topic_def.get("items", [])
        percent_mapped, capped_by_conflict = compute_knowledge_gap_pct(items)

        status_counts = {"satisfied": 0, "partial": 0, "missing": 0, "flagged_conflict": 0}
        for item in items:
            status = item.get("status", "missing")
            if status in status_counts:
                status_counts[status] += 1

        topics_block[topic_id] = {
            "epistemic_class": topic_def.get("epistemic_class"),
            "potential_reclass_target": topic_def.get("potential_reclass_target"),
            "percent_mapped": percent_mapped,
            "capped_by_conflict": capped_by_conflict,
            "total_checklist_items": len(items),
            "satisfied_count": status_counts["satisfied"],
            "partial_count": status_counts["partial"],
            "missing_count": status_counts["missing"],
            "flagged_conflict_count": status_counts["flagged_conflict"],
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        }

        results.append((topic_id, percent_mapped, capped_by_conflict,
                         topic_def.get("epistemic_class"), status_counts))

    weights_data["topics"] = topics_block

    with open(WEIGHTS_PATH, "w", encoding="utf-8", newline="") as f:
        json.dump(weights_data, f, indent=2, ensure_ascii=False)

    print()
    print(f"{'Topic':<35} {'%Mapped':>8} {'Capped':>7} {'Class':>6} {'S/P/M/F'}")
    print("-" * 80)
    for topic_id, pct, capped, epi_class, counts in results:
        spmf = f"{counts['satisfied']}/{counts['partial']}/{counts['missing']}/{counts['flagged_conflict']}"
        print(f"{topic_id:<35} {pct:>7.1f}% {str(capped):>7} {str(epi_class):>6} {spmf}")

    print()
    print(f"[OK] Synced {len(results)} topics into {WEIGHTS_PATH}")


if __name__ == "__main__":
    main()
