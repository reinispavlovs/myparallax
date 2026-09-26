#!/usr/bin/env python3
"""
scripts/review_cli.py
----------------------
Human-in-the-loop review CLI (Stabilization Priority #1).

Reads digests/cross_check.json (produced by digest_generator.py),
walks through every draft still in review_status == "pending" (re-checked
live against the .meta.json file, not just the digest snapshot), shows the
reviewer the computed credibility score, risk level, integrity/topic
warnings, skeptic critique and a content preview, then asks for a
decision: [a]pprove / [r]eject / [s]kip / [q]uit.

On approve/reject it updates the draft's .meta.json in place
(human_reviewed, review_status, reviewer, review_notes, reviewed_at) and
appends an audit record to digests/review_log.jsonl.

IMPORTANT: this tool does NOT move/promote files into content/articles/.
That is the job of the (not-yet-built) promote_drafts.py, which will only
act on drafts where review_status == "approved".

Usage:
    python scripts/review_cli.py
    python scripts/review_cli.py --reviewer "R.Pavlovs"
    python scripts/review_cli.py --digest path/to/other_cross_check.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Path setup ---------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = REPO_ROOT / "drafts"
DIGEST_PATH = REPO_ROOT / "digests" / "cross_check.json"
REVIEW_LOG_PATH = REPO_ROOT / "digests" / "review_log.jsonl"

RISK_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}  # HIGH reviewed first


# --- Helpers -------------------------------------------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8", newline="") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_log(record):
    REVIEW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REVIEW_LOG_PATH, "a", encoding="utf-8", newline="") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def html_preview(html_path, max_chars=500):
    try:
        raw = html_path.read_text(encoding="utf-8")
    except OSError as e:
        return f"[could not read {html_path.name}: {e}]"
    snippet = raw.strip().replace("\n", " ")
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars] + " ...[truncated]"
    return snippet


def sort_key(entry):
    """HIGH risk, integrity failures, invalid topics and conflicts get
    reviewed first — the riskiest drafts should never wait at the bottom
    of a long queue."""
    blocking = not (entry.get("content_hash_verified", True)
                     and entry.get("topic_valid", True))
    return (
        0 if blocking else 1,
        0 if entry.get("conflict_flag") else 1,
        RISK_ORDER.get(entry.get("risk_level", "MEDIUM"), 1),
        -entry.get("credibility_score_C_i", 0.0),
    )


def print_entry(entry, meta):
    print("\n" + "=" * 78)
    print(f"Draft:            {entry['draft_file']}")
    print(f"Topic:            {entry['topic_id']}  "
          f"(topic_valid={entry['topic_valid']})")
    print(f"Risk level:       {entry['risk_level']}")
    print(f"Credibility C_i:  {entry['credibility_score_C_i']}")
    print(f"Current weight:   {entry.get('current_topic_weight')}")
    print(f"arXiv found:      {entry['arxiv_source_found']}  "
          f"(note: arXiv is only ONE reference DB, not a definitive absence check)")
    print(f"Hash verified:    {entry['content_hash_verified']}")
    print(f"Conflict flag:    {entry['conflict_flag']}")
    print(f"Content flags:    {entry.get('recomputed_content_flags') or 'none'}")
    print(f"Auto-merge (sys): {entry['auto_merge_eligible']}")

    if not entry["content_hash_verified"]:
        print("  !! WARNING: content_hash mismatch — file may have been "
              "edited after generation. Verify manually before approving.")
    if not entry["topic_valid"]:
        print("  !! WARNING: topic_id is not in index.json's canonical list.")
    if entry["conflict_flag"]:
        print("  !! WARNING: another draft for the same topic exists in this batch.")

    critique = meta.get("skeptic_critique")
    if critique:
        print(f"\nSkeptic critique:\n  {critique}")

    print(f"\nContent preview:\n  {html_preview(DRAFTS_DIR / entry['draft_file'])}")
    print("=" * 78)


def prompt_decision():
    while True:
        choice = input("[a]pprove / [r]eject / [s]kip / [q]uit > ").strip().lower()
        if choice in ("a", "approve"):
            return "approve"
        if choice in ("r", "reject"):
            return "reject"
        if choice in ("s", "skip"):
            return "skip"
        if choice in ("q", "quit"):
            return "quit"
        print("  invalid input — type a, r, s, or q.")


def update_meta(meta_path, meta, decision, reviewer, notes):
    now = datetime.now(timezone.utc).isoformat()
    meta["human_reviewed"] = True
    meta["review_status"] = "approved" if decision == "approve" else "rejected"
    meta["reviewer"] = reviewer
    meta["review_notes"] = notes
    meta["reviewed_at"] = now
    save_json(meta_path, meta)
    return now


# --- Main ------------------------------------------------------------------

def run_review(digest_path=DIGEST_PATH, reviewer=None):
    if not digest_path.exists():
        print(f"[ERROR] Digest not found at {digest_path}. "
              f"Run digest_generator.py first.")
        sys.exit(1)

    digest = load_json(digest_path)
    entries = digest.get("entries", [])

    if not reviewer:
        reviewer = input("Reviewer name/initials: ").strip() or "anonymous"

    counts = {"approved": 0, "rejected": 0, "skipped": 0}
    pending_entries = []

    for entry in entries:
        meta_path = DRAFTS_DIR / entry["meta_file"]
        if not meta_path.exists():
            print(f"[WARN] meta file missing on disk, skipping: {entry['meta_file']}")
            continue
        meta = load_json(meta_path)
        # Re-check LIVE status, not the digest snapshot — the digest may be
        # stale if this CLI (or another reviewer) already acted on it.
        if meta.get("review_status", "pending") != "pending":
            continue
        pending_entries.append((entry, meta, meta_path))

    if not pending_entries:
        print("[OK] No pending drafts to review. All caught up.")
        return counts

    pending_entries.sort(key=lambda triple: sort_key(triple[0]))

    print(f"[OK] {len(pending_entries)} draft(s) pending review. "
          f"Riskiest/blocking drafts shown first.\n")

    for entry, meta, meta_path in pending_entries:
        print_entry(entry, meta)
        decision = prompt_decision()

        if decision == "quit":
            print("\n[STOP] Quitting review session early.")
            break
        if decision == "skip":
            counts["skipped"] += 1
            continue

        notes = input("Review notes (optional): ").strip()
        reviewed_at = update_meta(meta_path, meta, decision, reviewer, notes)

        append_log({
            "timestamp": reviewed_at,
            "reviewer": reviewer,
            "draft_file": entry["draft_file"],
            "meta_file": entry["meta_file"],
            "topic_id": entry["topic_id"],
            "decision": decision,
            "credibility_score_at_review": entry["credibility_score_C_i"],
            "risk_level": entry["risk_level"],
            "notes": notes,
        })

        counts["approved" if decision == "approve" else "rejected"] += 1
        print(f"  -> saved: review_status={meta['review_status']} "
              f"(reviewer={reviewer})")

    print("\n" + "-" * 40)
    print(f"Session summary: approved={counts['approved']} "
          f"rejected={counts['rejected']} skipped={counts['skipped']}")
    print(f"Audit log: {REVIEW_LOG_PATH}")
    print("-" * 40)
    return counts


def main():
    parser = argparse.ArgumentParser(description="Human-in-the-loop draft review CLI")
    parser.add_argument("--reviewer", default=None, help="Reviewer name/initials")
    parser.add_argument("--digest", default=str(DIGEST_PATH),
                         help="Path to cross_check.json (default: digests/cross_check.json)")
    args = parser.parse_args()

    try:
        run_review(digest_path=Path(args.digest), reviewer=args.reviewer)
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted by user (Ctrl+C). No further changes saved.")
        sys.exit(130)


if __name__ == "__main__":
    main()
