"""
scripts/shared/claim_layers_utils.py

Shared logic for parsing, validating, and scoring claim_layers
across digest_generator.py and topic_weights_calculator.py.

Source of truth for structure: content/articles/topic_weights.schema.example.json
"""

import re

FORBIDDEN_ABSOLUTE_TERMS = [
    "proves", "proven", "definitively", "undeniably", "certainly",
    "always", "never", "impossible", "confirmed fact"
]

PRECISE_DECIMAL_PATTERN = re.compile(r"\b\d+\.\d{2,}\b")

# Decision #61: negation-awareness for precise-decimal flagging.
# Prevents false positives where a number is explicitly disclaimed/removed
# in the surrounding narrative (e.g. "A previous version hardcoded 0.84
# ... it has been removed.").
NEGATION_MARKER_PATTERN = re.compile(
    r"(has been removed|was removed|no longer includes?|not included|"
    r"without (a |any )?citation|previous version|placeholder value|"
    r"has since been removed|removed (it|this|the value)|was not included|"
    r"does not include)",
    re.IGNORECASE,
)
SOURCE_MARKER_PATTERN = re.compile(r"\[(source|ref|arxiv):[^\]]+\]", re.IGNORECASE)

BASE_WEIGHTS_BY_RISK = {
    "LOW": 3.0,
    "MEDIUM": 1.5,
    "HIGH": 0.5,
}

MULTIPLIER_ARXIV_SOURCE = 1.3
MULTIPLIER_CONFLICT = 0.5


def normalize_claim_layers(draft_data: dict) -> list[dict]:
    """
    Ensures every draft has a consistent claim_layers structure,
    regardless of when/how it was generated (legacy fallback).

    Legacy drafts (pre-refactor, from _archive/raw_generations/ or
    early main.py outputs) may lack claim_layers entirely. In that
    case, synthesize a single pseudo-layer marked as unverified.
    """
    layers = draft_data.get("claim_layers")

    if not layers:
        # Legacy fallback — schema violation, but don't crash the pipeline
        return [{
            "layer_type": "inferential_bridge",
            "text": draft_data.get("body", "")[:500],
            "stance": draft_data.get("stance", "unresolved"),
            "confidence": draft_data.get("confidence", None),
            "risk_level": "MEDIUM",  # forced minimum per decision #21
            "bridge_verified": False,
            "arxiv_source_found": False,
            "evidence_level": None,
            "conflict_detected": False,
            "counts_toward_topic": True,
            "is_legacy_synthesized": True,
        }]

    normalized = []
    for layer in layers:
        normalized.append({
            "layer_type": layer.get("layer_type", "inferential_bridge"),
            "text": layer.get("text", ""),
            "stance": layer.get("stance", "unresolved"),
            "confidence": layer.get("confidence"),
            "risk_level": layer.get("risk_level", "MEDIUM"),
            "bridge_verified": layer.get("bridge_verified", False),
            "arxiv_source_found": layer.get("arxiv_source_found", False),
            "evidence_level": layer.get("evidence_level"),
            "conflict_detected": layer.get("conflict_detected", False),
            "counts_toward_topic": layer.get("counts_toward_topic", False),
            "is_legacy_synthesized": False,
        })
    return normalized


def compute_credibility_coefficient(layer: dict) -> float:
    """
    C_i per decision #5, #17, #22.
    Base weight by risk_level, modified by multipliers.
    Unverified bridges already forced risk_level=MEDIUM upstream (decision #21).
    """
    risk_level = layer.get("risk_level", "MEDIUM")
    c_i = BASE_WEIGHTS_BY_RISK.get(risk_level, 1.5)

    if layer.get("arxiv_source_found"):
        c_i *= MULTIPLIER_ARXIV_SOURCE

    if layer.get("conflict_detected"):
        c_i *= MULTIPLIER_CONFLICT

    return c_i


def resolve_stance_value(layer: dict, global_config: dict) -> float | None:
    """
    Maps stance -> numeric S_i per global_config.stance_values.
    Returns None if stance is unresolved (excluded from Bayesian sum,
    flagged for review per decision #22).
    """
    stance_values = global_config.get("stance_values", {})
    stance = layer.get("stance")

    if stance not in stance_values:
        return None  # unresolved -> caller must flag needs-human-review

    return stance_values[stance]


def is_eligible_for_bayesian_sum(layer: dict) -> bool:
    """
    Decision #18: only counts_toward_topic: true layers contribute.
    """
    return layer.get("counts_toward_topic", False) is True


def determine_auto_merge_eligibility(layers: list[dict]) -> tuple[bool, list[str]]:
    """
    Decision #21. Returns (eligible, reasons_blocked).
    """
    reasons = []

    for layer in layers:
        if layer.get("risk_level") == "HIGH":
            reasons.append("HIGH risk_level present")
        if layer.get("layer_type") == "inferential_bridge" and not layer.get("bridge_verified", False):
            reasons.append("Unverified inferential_bridge present")
        if layer.get("conflict_detected"):
            reasons.append("Conflict detected in metadata")

    return (len(reasons) == 0, list(set(reasons)))


def validate_content_flags(layer: dict) -> list[str]:
    """
    Decision #24. Returns list of flag strings for a single layer.
    """
    flags = []
    text = layer.get("text", "")

    for term in FORBIDDEN_ABSOLUTE_TERMS:
        if re.search(rf"\b{term}\b", text, re.IGNORECASE):
            flags.append(f"forbidden_absolute_term:{term}")

    for match in PRECISE_DECIMAL_PATTERN.finditer(text):
        # check if a source marker exists within reasonable proximity
        window = text[max(0, match.start() - 80):match.end() + 80]
        if NEGATION_MARKER_PATTERN.search(window):
            continue  # Decision #61: skip flag if value is explicitly negated/removed
        if not SOURCE_MARKER_PATTERN.search(window):
            flags.append(f"unsourced_precise_decimal:{match.group()}")

    if layer.get("counts_toward_topic") and not layer.get("evidence_level"):
        flags.append("missing_evidence_level_on_weighted_layer")

    return flags


def calculate_credibility_score(risk_level: str, arxiv_source_found: bool = False,
                                 conflict_flag: bool = False) -> float:
    """
    Draft-level adapter for digest_generator.py.

    digest_generator.py currently scores ONE risk_level per draft
    (read from meta.json root, not from claim_layers), because main.py
    does not yet emit a claim_layers array (see action item #8).
    This wraps compute_credibility_coefficient() so BASE_WEIGHTS_BY_RISK
    and the multipliers stay defined in exactly one place.

    TODO(#8): once main.py writes real claim_layers per draft,
    digest_generator.py should call normalize_claim_layers() +
    compute_credibility_coefficient() per layer directly, and this
    adapter should be deleted.
    """
    synthetic_layer = {
        "risk_level": risk_level,
        "arxiv_source_found": arxiv_source_found,
        "conflict_detected": conflict_flag,
    }
    return round(compute_credibility_coefficient(synthetic_layer), 3)
# --- Knowledge Gap % (checklist-based) ---

CHECKLIST_STATUS_WEIGHTS = {
    "satisfied": 1.0,
    "partial": 0.5,
    "missing": 0.0,
    "flagged_conflict": 0.0,
}

FLAGGED_CONFLICT_CAP_PCT = 60.0


def compute_knowledge_gap_pct(checklist_items: list) -> tuple:
    """
    checklist_items: list of dicts, each containing at least a "status" key
    (values: "satisfied", "partial", "missing", "flagged_conflict").

    Returns (percent_mapped: float, capped_by_conflict: bool).

    If any item is flagged_conflict, the resulting percent is hard-capped
    at FLAGGED_CONFLICT_CAP_PCT regardless of the raw weighted average,
    to prevent an unresolved epistemic conflict from being masked by
    an otherwise-high score.
    """
    if not checklist_items:
        return (0.0, False)

    total = len(checklist_items)
    weight_sum = 0.0
    has_conflict = False

    for item in checklist_items:
        status = item.get("status", "missing")
        weight_sum += CHECKLIST_STATUS_WEIGHTS.get(status, 0.0)
        if status == "flagged_conflict":
            has_conflict = True

    raw_pct = (weight_sum / total) * 100.0

    if has_conflict and raw_pct > FLAGGED_CONFLICT_CAP_PCT:
        return (round(FLAGGED_CONFLICT_CAP_PCT, 1), True)

    return (round(raw_pct, 1), has_conflict)

