#!/usr/bin/env python3
"""
promote_drafts.py
------------------
Promotes human-approved drafts from drafts/ into
content/articles/, and updates the canonical index.json + topic_weights.json.

This is the ONLY script allowed to write into content/articles/. Everything
upstream (main.py, review_cli.py) only ever touches drafts/.

Pipeline position:
    main.py -> digest_generator.py -> review_cli.py (human decision) -> HERE

Safety rules enforced:
  1. Only acts on drafts where meta["review_status"] == "approved" AND
     meta["human_reviewed"] is True.
  2. Skips drafts already marked meta["promoted"] == True (idempotent —
     safe to re-run).
  3. Re-verifies content_hash against the live .html file right before
     promoting — if the file was edited after approval, it is REJECTED
     and flagged, never silently promoted.
  4. If a topic already has a published article, the old file is backed
     up (content/articles/_history/) before being overwritten, and the
     new draft's credibility score must be >= old one unless --force.
  5. topic_weights.json is updated with a simple placeholder bump
     (documented as TEMPORARY — see topic_weights_calculator.py TODO,
     stabilization item #18). This is NOT the final weighting algorithm.

Usage:
    python scripts/promote_drafts.py --dry-run
    python scripts/promote_drafts.py
    python scripts/promote_drafts.py --topic megalithic_engineering_acoustics
    python scripts/promote_drafts.py --force
"""

import argparse
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# --- Path setup ----------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = REPO_ROOT / "drafts"
ARTICLES_DIR = REPO_ROOT / "content" / "articles"
HISTORY_DIR = ARTICLES_DIR / "_history"
INDEX_PATH = ARTICLES_DIR / "index.json"
WEIGHTS_PATH = ARTICLES_DIR / "topic_weights.json"
PROMOTED_ARCHIVE_DIR = DRAFTS_DIR / "_promoted"
PROMOTE_LOG_PATH = REPO_ROOT / "digests" / "promote_log.jsonl"


# --- IO helpers ------------------------------------------------------------

def load_json(path, default=None):
    if not path.exists():
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_meta(meta_path, meta):
    save_json(meta_path, meta)


def append_log(record):
    PROMOTE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROMOTE_LOG_PATH, "a", encoding="utf-8", newline="") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def sha256_of_file(path, n_chars=12):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:n_chars]


def safe_move(src, dst, retries=5, delay=0.3):
    """Retry shutil.move to survive transient OneDrive/AV file locks.

    Fixes Regression #160: shutil.move() failing right after shutil.copy2()
    because a sync client (e.g. OneDrive) briefly holds a handle on the
    just-written file. Uses simple linear backoff. Does NOT raise -- caller
    must check the boolean return value.
    """
    last_err = None
    for attempt in range(retries):
        try:
            shutil.move(str(src), str(dst))
            return True
        except OSError as e:
            last_err = e
            time.sleep(delay * (attempt + 1))
    print(f"  [WARN] safe_move failed after {retries} attempts "
          f"({src} -> {dst}): {last_err}")
    return False


# --- index.json / topic_weights.json helpers --------------------------------

def get_topics_dict(index_data):
    """index.json is expected to look like:
        { "topics": { "<topic_id>": {...}, ... } }
    but we defensively support a flat dict too, and auto-migrate.
    """
    if "topics" in index_data and isinstance(index_data["topics"], dict):
        return index_data["topics"]
    # legacy/flat fallback: whole file is the topics dict
    if all(isinstance(v, dict) for v in index_data.values()) and index_data:
        return index_data
    return {}


def ensure_index_shape(index_data):
    if "topics" not in index_data:
        index_data = {"topics": get_topics_dict(index_data), "schema": "1.0"}
    return index_data


def bump_weight(existing_weight, credibility_score, risk_level):
    """
    TEMPORARY placeholder weighting bump.
    TODO(stabilization #18): replace with topic_weights_calculator.py output.

    Logic (intentionally simple & conservative):
      - Normalize C_i (assumed roughly 0-3 range from BASE_WEIGHTS_BY_RISK)
        into a 0-1 nudge.
      - HIGH risk articles get zero bump (they shouldn't be auto-merge
        eligible anyway, but a human can still force-promote one).
      - Weight is clamped to [0.1, 5.0] to avoid runaway drift.
    """
    if existing_weight is None:
        existing_weight = 1.0
    if risk_level == "HIGH":
        nudge = 0.0
    else:
        nudge = min(max(credibility_score, 0.0), 3.0) / 3.0 * 0.25  # max +0.25
    new_weight = existing_weight + nudge
    return round(min(max(new_weight, 0.1), 5.0), 4)


# --- Core promotion logic ----------------------------------------------------

def find_approved_drafts(topic_filter=None):
    """Scan DRAFTS_DIR directly for .meta.json — independent from the
    digest, since the digest may be stale relative to review_cli edits."""
    candidates = []
    for meta_path in sorted(DRAFTS_DIR.glob("*.meta.json")):
        try:
            meta = load_json(meta_path)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[WARN] could not read {meta_path.name}: {e}")
            continue

        if meta.get("review_status") != "approved":
            continue
        if not meta.get("human_reviewed"):
            print(f"[WARN] {meta_path.name} has review_status=approved but "
                  f"human_reviewed=False — skipping out of caution.")
            continue
        if meta.get("promoted") is True:
            continue
        if topic_filter and meta.get("topic_id") != topic_filter:
            continue

        html_path = DRAFTS_DIR / meta.get("content_file", "")
        if not html_path.exists():
            print(f"[WARN] {meta_path.name} approved but content_file "
                  f"missing on disk: {meta.get('content_file')} — skipping.")
            continue

        candidates.append((meta_path, meta, html_path))
    return candidates


def verify_hash_integrity(meta, html_path):
    live_hash = sha256_of_file(html_path)
    stored_hash = meta.get("content_hash")
    return live_hash == stored_hash, live_hash, stored_hash


def promote_one(meta_path, meta, html_path, index_data, weights_data,
                 force=False, dry_run=False):
    topic_id = meta.get("topic_id")
    topics = get_topics_dict(index_data)

    ok, live_hash, stored_hash = verify_hash_integrity(meta, html_path)
    if not ok:
        print(f"[REJECT] {meta_path.name}: content_hash mismatch "
              f"(stored={stored_hash}, live={live_hash}). File was edited "
              f"after approval — NOT promoting. Re-review required.")
        return "rejected_hash_mismatch"

    new_score = meta.get("credibility_score_C_i")
    if new_score is None:
        print(f"[REJECT] {meta_path.name}: credibility_score_C_i is missing "
              f"from metadata. Refusing to promote without a verified score "
              f"— run digest_generator.py to compute and persist it first.")
        return "rejected_missing_score"

    existing_entry = topics.get(topic_id)
    if existing_entry and not force:
        old_score = existing_entry.get("credibility_score", 0.0)
        if new_score < old_score:
            print(f"[SKIP] {meta_path.name}: new credibility_score "
                  f"({new_score}) is lower than currently published "
                  f"({old_score}) for topic '{topic_id}'. Use --force to "
                  f"override.")
            return "skipped_lower_score"

    dest_filename = f"{topic_id}.html"
    dest_path = ARTICLES_DIR / dest_filename

    print(f"[PLAN] Promote {html_path.name} -> content/articles/{dest_filename} "
          f"(topic='{topic_id}', score={new_score}, risk={meta.get('risk_level') or meta.get('claim_layers')})")

    if dry_run:
        return "dry_run_ok"

    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Backup existing published article, if any
    if dest_path.exists():
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = HISTORY_DIR / f"{topic_id}-{timestamp}.html"
        shutil.copy2(dest_path, backup_path)
        print(f"  backed up old article -> {backup_path.relative_to(REPO_ROOT)}")

    # 2. Copy (not move) the draft HTML into content/articles/
    shutil.copy2(html_path, dest_path)

    # 3. Update index.json
    topics[topic_id] = {
        "topic_id": topic_id,
        "topic_name": meta.get("topic_name"),
        "article_file": dest_filename,
        "content_hash": live_hash,
        "credibility_score": new_score,
        "risk_level": meta.get("risk_level"),
        "generated_at": meta.get("generated_at"),
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "source_draft": meta.get("content_file"),
        "reviewer": meta.get("reviewer"),
    }
    index_data["topics"] = topics

    # 4. Update topic_weights.json (placeholder logic, see bump_weight())
    old_weight = weights_data.get(topic_id)
    weights_data[topic_id] = bump_weight(
        old_weight, new_score, meta.get("risk_level")
    )

    # 5. Mark draft meta as promoted (idempotency)
    meta["promoted"] = True
    meta["promoted_at"] = datetime.now(timezone.utc).isoformat()
    save_meta(meta_path, meta)

    # 6. Archive the promoted draft files out of the active drafts/ folder
    #    to prevent directory pollution and stale batch-conflict false positives
    #    in digest_generator.py on subsequent runs.
    PROMOTED_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archived_html = PROMOTED_ARCHIVE_DIR / html_path.name
    archived_meta = PROMOTED_ARCHIVE_DIR / meta_path.name
    ok_html = safe_move(html_path, archived_html)
    ok_meta = safe_move(meta_path, archived_meta)
    if ok_html and ok_meta:
        print("  archived draft ->", archived_html.name, "(+ .meta.json)")
    else:
        print("  [WARN] promotion succeeded but archiving failed permanently.")
        print("  Draft remains in drafts/ but is marked promoted=True (idempotent).")

    append_log({
        "timestamp": meta["promoted_at"],
        "topic_id": topic_id,
        "draft_file": meta.get("content_file"),
        "meta_file": meta_path.name,
        "article_file": dest_filename,
        "credibility_score": new_score,
        "old_weight": old_weight,
        "new_weight": weights_data[topic_id],
        "forced": force,
    })

    print(f"  [OK] promoted. topic_weights[{topic_id}]: "
          f"{old_weight} -> {weights_data[topic_id]}")
    return "promoted"


def run_promotion(topic_filter=None, force=False, dry_run=False):
    index_data = ensure_index_shape(load_json(INDEX_PATH, default={"topics": {}}))
    weights_data = load_json(WEIGHTS_PATH, default={})

    candidates = find_approved_drafts(topic_filter=topic_filter)
    if not candidates:
        print("[OK] No approved, un-promoted drafts found.")
        return

    print(f"[OK] {len(candidates)} approved draft(s) found for promotion.\n")

    results = {}
    for meta_path, meta, html_path in candidates:
        outcome = promote_one(
            meta_path, meta, html_path, index_data, weights_data,
            force=force, dry_run=dry_run,
        )
        results[outcome] = results.get(outcome, 0) + 1

    if not dry_run:
        save_json(INDEX_PATH, index_data)
        save_json(WEIGHTS_PATH, weights_data)
        print(f"\n[OK] Wrote {INDEX_PATH.relative_to(REPO_ROOT)}")
        print(f"[OK] Wrote {WEIGHTS_PATH.relative_to(REPO_ROOT)}")
    else:
        print("\n[DRY RUN] No files were written (index.json / "
              "topic_weights.json / meta.json unchanged).")

    print("\n" + "-" * 40)
    print("Summary:", results)
    print("-" * 40)


def main():
    parser = argparse.ArgumentParser(description="Promote approved drafts to content/articles/")
    parser.add_argument("--topic", default=None,
                         help="Only promote drafts for this topic_id")
    parser.add_argument("--force", action="store_true",
                         help="Override the 'new score must be >= old score' guard")
    parser.add_argument("--dry-run", action="store_true",
                         help="Show what would happen without writing anything")
    args = parser.parse_args()

    try:
        run_promotion(topic_filter=args.topic, force=args.force, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted. No partial writes committed for index/weights.")
        sys.exit(130)


if __name__ == "__main__":
    main()
