import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(".").resolve()
INDEX_PATH = REPO_ROOT / "content" / "articles" / "index.json"
DRAFTS_DIR = REPO_ROOT / "drafts"

# --- Backup index.json first ---
backup_dir = REPO_ROOT / "content" / "articles" / "_history"
backup_dir.mkdir(parents=True, exist_ok=True)
ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup_path = backup_dir / f"index.json.bak.{ts}"
shutil.copy2(INDEX_PATH, backup_path)
print(f"[OK] Backed up index.json -> {backup_path.relative_to(REPO_ROOT)}")

index_data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
topics = index_data.get("topics", {})

# --- Build: for each topic_id, find the MOST RECENTLY promoted draft ---
best_by_topic = {}  # topic_id -> (promoted_at_str, risk_level, meta_filename)
for mf in DRAFTS_DIR.glob("*.meta.json"):
    meta = json.loads(mf.read_text(encoding="utf-8"))
    if not meta.get("promoted"):
        continue
    tid = meta.get("topic_id")
    p_at = meta.get("promoted_at") or ""
    risk = meta.get("risk_level")
    if tid not in best_by_topic or p_at > best_by_topic[tid][0]:
        best_by_topic[tid] = (p_at, risk, mf.name)

print()
print("=== Backfill plan ===")
changed = 0
for tid, entry in topics.items():
    if tid not in best_by_topic:
        print(f"[SKIP] {tid}: no promoted draft found on disk.")
        continue
    p_at, risk, mf_name = best_by_topic[tid]
    old_risk = entry.get("risk_level")
    if old_risk == risk:
        print(f"[NOOP] {tid}: risk_level already '{risk}' (source: {mf_name})")
        continue
    print(f"[FIX]  {tid}: risk_level {old_risk!r} -> {risk!r} (source: {mf_name}, promoted_at={p_at})")
    entry["risk_level"] = risk
    changed += 1

index_data["topics"] = topics

if changed:
    INDEX_PATH.write_text(json.dumps(index_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Wrote {changed} risk_level backfill(s) to {INDEX_PATH.relative_to(REPO_ROOT)}")
else:
    print("\n[OK] No changes needed.")
