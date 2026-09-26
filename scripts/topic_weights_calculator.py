#!/usr/bin/env python3
"""
scripts/topic_weights_calculator.py

Standalone module invoked by promote_drafts.yml. Aggregates a batch of
promoted articles' claim_layers and updates topic_weights.json (SSOT)
using a credibility-weighted Bayesian moving average.

Formula (decision #4):
    new_weight = (current_weight * N0 + Σ(S_i * C_i)) / (N0 + Σ C_i)

Critically: ALL layers for a topic across the ENTIRE batch are collected
BEFORE the formula is applied once (decision #20) — this prevents
order-dependency bias where article A processed before article B would
yield a different result than B before A.

Dependencies: PyYAML
"""

import argparse
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from shared.claim_layers_utils import (
    normalize_claim_layers,
    compute_credibility_coefficient,
    resolve_stance_value,
    is_eligible_for_bayesian_sum,
    determine_auto_merge_eligibility,
    validate_content_flags,
)

TOPIC_WEIGHTS_PATH_DEFAULT = "content/articles/topic_weights.json"
FRONTMATTER_DELIM = "---"
RESERVED_TOP_LEVEL_KEYS = {"global_config"}


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_topic_weights(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_topic_weights(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def parse_frontmatter(article_path: str) -> dict:
    """
    Minimal YAML frontmatter parser for article .md files:
        ---
        <yaml block: topic_id, claim_layers, checklist_items_satisfied...>
        ---
        <markdown body>
    """
    text = Path(article_path).read_text(encoding="utf-8")
    if not text.startswith(FRONTMATTER_DELIM):
        return {}

    parts = text.split(FRONTMATTER_DELIM, 2)
    if len(parts) < 3:
        return {}

    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        print(f"[WARN] Could not parse frontmatter for {article_path}: {e}", file=sys.stderr)
        return {}

    meta["_source_path"] = article_path
    return meta


def discover_batch_files(explicit_paths: list[str] | None) -> list[str]:
    """
    Resolves which article files this run should process.
    Priority: explicit CLI paths (from `git diff` in the workflow) >
    fallback full glob over content/articles/ (manual/dry-run exploration).
    """
    if explicit_paths:
        return [p for p in explicit_paths if p.endswith(".md")]
    return sorted(glob.glob("content/articles/**/*.md", recursive=True))


def get_topic_entries(weights_data: dict) -> dict:
    """
    Decision #13: topic_weights.json is a FLAT dict — topic_key IS the
    top-level key. global_config is the only reserved sibling key.
    """
    return {k: v for k, v in weights_data.items() if k not in RESERVED_TOP_LEVEL_KEYS}


# ---------------------------------------------------------------------------
# Risk enforcement guard
# ---------------------------------------------------------------------------

def _enforce_minimum_risk_for_unverified_bridges(layer: dict) -> dict:
    """
    Decision #21: unverified inferential_bridge layers must never be scored
    as LOW risk, regardless of what upstream generation (main.py) claimed.

    NOTE — DRY debt flag: this logic conceptually belongs in
    claim_layers_utils.normalize_claim_layers(), since digest_generator.py
    will need the identical guard. Kept local here to avoid re-touching the
    already-approved shared module without review. Candidate for migration
    when digest_generator.py is built.
    """
    if layer.get("layer_type") == "inferential_bridge" and not layer.get("bridge_verified", False):
        if layer.get("risk_level") == "LOW":
            layer = {**layer, "risk_level": "MEDIUM"}
    return layer


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------

def aggregate_batch_by_topic(article_metas: list[dict]) -> dict:
    """
    Groups normalized, risk-enforced claim_layers by topic_id across the
    ENTIRE batch. Nothing is scored until this collection is complete.
    """
    by_topic: dict[str, dict] = {}

    for meta in article_metas:
        topic_id = meta.get("topic_id")
        if not topic_id:
            print(f"[WARN] {meta.get('_source_path')} has no topic_id — skipped.", file=sys.stderr)
            continue

        layers = normalize_claim_layers(meta)
        layers = [_enforce_minimum_risk_for_unverified_bridges(l) for l in layers]

        entry = by_topic.setdefault(topic_id, {"layers": [], "articles": []})
        entry["articles"].append(meta.get("_source_path"))
        for layer in layers:
            layer["_source_article"] = meta.get("_source_path")
            entry["layers"].append(layer)

    return by_topic


def compute_topic_weight_update(current_weight: float, layers: list[dict], global_config: dict) -> dict:
    """
    new_weight = (current_weight * N0 + Σ(S_i * C_i)) / (N0 + Σ C_i)

    Only layers where counts_toward_topic=True AND stance resolves to a
    known value contribute (decisions #18, #22).
    """
    n0 = global_config.get("N0_stability_coefficient", 20.0)

    weighted_stance_sum = 0.0
    credibility_sum = 0.0
    contributing_count = 0
    unresolved_flagged = []
    content_flags = []

    for layer in layers:
        content_flags.extend(validate_content_flags(layer))

        if not is_eligible_for_bayesian_sum(layer):
            continue

        s_i = resolve_stance_value(layer, global_config)
        if s_i is None:
            unresolved_flagged.append(layer.get("_source_article"))
            continue

        c_i = compute_credibility_coefficient(layer)
        weighted_stance_sum += s_i * c_i
        credibility_sum += c_i
        contributing_count += 1

    if credibility_sum == 0.0:
        new_weight = current_weight  # no eligible evidence — stable
    else:
        new_weight = (current_weight * n0 + weighted_stance_sum) / (n0 + credibility_sum)

    return {
        "new_weight": round(new_weight, 4),
        "contributing_layers": contributing_count,
        "credibility_sum": round(credibility_sum, 4),
        "unresolved_flagged_articles": sorted(set(unresolved_flagged)),
        "content_flags": content_flags,
    }


def check_pending_reclassification(topic_entry: dict, layers: list[dict]) -> bool:
    """
    Decision #23: the calculator NEVER auto-changes epistemic_class.
    It only raises pending_reclassification_review=True when a Class C
    topic accumulates a verified bridge with B/A-level evidence — signaling
    that the C→B Reclassification Test criteria (mechanism, falsifiable
    prediction, reproducibility, controlled test) may now be satisfiable.
    """
    if topic_entry.get("epistemic_class") != "C":
        return topic_entry.get("pending_reclassification_review", False)

    for layer in layers:
        if (
            layer.get("layer_type") == "inferential_bridge"
            and layer.get("bridge_verified") is True
            and layer.get("evidence_level") in ("A", "B")
        ):
            return True

    return topic_entry.get("pending_reclassification_review", False)


def update_data_completeness(topic_entry: dict, articles_for_topic: list[dict]) -> dict:
    """
    Decision #14/#19: percent_mapped stays strictly deterministic —
    derived only from total_checklist_items / completed_items counts.

    This function only ADDS newly satisfied checklist item ids, declared
    explicitly in frontmatter as `checklist_items_satisfied: [...]`, and
    appends new falsifiability gaps via `checklist_items_missing: [...]`.
    It never touches total_checklist_items — that ceiling is human-owned.

    ASSUMPTION FLAG: field names `checklist_items_satisfied` /
    `checklist_items_missing` are my proposal for the frontmatter contract.
    Please confirm these match topic_weights.schema.example.json, or tell
    me the correct names and I'll adjust.
    """
    dc = dict(topic_entry.get("data_completeness", {
        "total_checklist_items": 0,
        "completed_items": 0,
        "missing_items": [],
        "satisfied_item_ids": [],
    }))

    satisfied = set(dc.get("satisfied_item_ids", []))
    missing = list(dc.get("missing_items", []))

    for meta in articles_for_topic:
        for item_id in meta.get("checklist_items_satisfied", []):
            satisfied.add(item_id)
            missing = [m for m in missing if m != item_id]

        for new_missing in meta.get("checklist_items_missing", []):
            if new_missing not in missing:
                missing.append(new_missing)

    dc["satisfied_item_ids"] = sorted(satisfied)
    dc["completed_items"] = len(satisfied)
    dc["missing_items"] = missing

    total = dc.get("total_checklist_items", 0)
    dc["percent_mapped"] = round((len(satisfied) / total) * 100, 2) if total > 0 else 0.0

    return dc


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run(topic_weights_path: str, batch_files: list[str] | None, pr_number: str | None, dry_run: bool) -> dict:
    weights_data = load_topic_weights(topic_weights_path)
    global_config = weights_data.get("global_config", {})
    topic_entries = get_topic_entries(weights_data)  # same object refs as weights_data

    files = discover_batch_files(batch_files)
    if not files:
        print("[INFO] No article files found for this batch. Nothing to do.")
        return {"status": "noop", "topics": {}, "batch_auto_merge_eligible": True, "batch_block_reasons": []}

    article_metas = [m for m in (parse_frontmatter(f) for f in files) if m]
    by_topic = aggregate_batch_by_topic(article_metas)

    report = {"status": "ok", "dry_run": dry_run, "pr_number": pr_number, "topics": {}}
    batch_blocked_reasons = []

    for topic_id, batch in by_topic.items():
        topic_entry = topic_entries.get(topic_id)
        if topic_entry is None:
            print(f"[WARN] Unknown topic_id '{topic_id}' — not in topic_weights.json. Skipped.", file=sys.stderr)
            continue

        layers = batch["layers"]
        articles_meta = [m for m in article_metas if m.get("_source_path") in batch["articles"]]

        update = compute_topic_weight_update(
            current_weight=topic_entry.get("weight", 50.0),
            layers=layers,
            global_config=global_config,
        )

        eligible, block_reasons = determine_auto_merge_eligibility(layers)
        if not eligible:
            batch_blocked_reasons.extend(block_reasons)

        pending_reclass = check_pending_reclassification(topic_entry, layers)
        new_data_completeness = update_data_completeness(topic_entry, articles_meta)

        history_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pr_number": pr_number,
            "previous_weight": topic_entry.get("weight"),
            "new_weight": update["new_weight"],
            "contributing_layers": update["contributing_layers"],
            "credibility_sum": update["credibility_sum"],
        }

        report["topics"][topic_id] = {
            "previous_weight": topic_entry.get("weight"),
            "new_weight": update["new_weight"],
            "contributing_layers": update["contributing_layers"],
            "unresolved_flagged_articles": update["unresolved_flagged_articles"],
            "content_flags": update["content_flags"],
            "pending_reclassification_review": pending_reclass,
            "auto_merge_eligible": eligible,
            "block_reasons": block_reasons,
            "data_completeness": new_data_completeness,
        }

        if not dry_run:
            topic_entry["weight"] = update["new_weight"]
            topic_entry.setdefault("weight_history", []).append(history_entry)
            topic_entry["pending_reclassification_review"] = pending_reclass
            topic_entry["data_completeness"] = new_data_completeness

    report["batch_auto_merge_eligible"] = len(batch_blocked_reasons) == 0
    report["batch_block_reasons"] = sorted(set(batch_blocked_reasons))

    if not dry_run:
        save_topic_weights(topic_weights_path, weights_data)

    return report


def main():
    parser = argparse.ArgumentParser(description="Aggregate claim_layers into topic_weights.json updates.")
    parser.add_argument("--topic-weights", default=TOPIC_WEIGHTS_PATH_DEFAULT)
    parser.add_argument("--batch-files", nargs="*", default=None,
                         help="Explicit article paths (e.g. from `git diff`). Defaults to full content/articles/ scan.")
    parser.add_argument("--pr-number", default=None)
    parser.add_argument("--dry-run", action="store_true",
                         help="Compute and print the report WITHOUT writing topic_weights.json")
    parser.add_argument("--output-report", default=None,
                         help="Optional path to write the JSON report (for CI to post as a PR comment)")
    args = parser.parse_args()

    report = run(
        topic_weights_path=args.topic_weights,
        batch_files=args.batch_files,
        pr_number=args.pr_number,
        dry_run=args.dry_run,
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.output_report:
        with open(args.output_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    # IMPORTANT: blocked status fails the check EVEN in --dry-run.
    # Dry-run only controls whether topic_weights.json is WRITTEN — it must
    # still fail the CI status check so GitHub blocks the merge on preview.
    if not report.get("batch_auto_merge_eligible", True):
        print("\n[BLOCKED] This batch is NOT eligible for auto-merge:", file=sys.stderr)
        for reason in report.get("batch_block_reasons", []):
            print(f"  - {reason}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
