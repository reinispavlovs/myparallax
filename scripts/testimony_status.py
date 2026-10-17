#!/usr/bin/env python3
"""Build content/articles/testimony_status.json from the narrative corpus.

Reads
  narrative_corpus/sources.json          registry of candidate sources and their access status
  narrative_corpus/data/*.jsonl          one record per line (see narrative_corpus/schema.json)
  narrative_corpus/data/reliability.json optional: {"motif_code": kappa, ...} from double coding

Writes
  content/articles/testimony_status.json (shown on tribunal.html)

Rules (SPEC.md):
  * Only sources whose access_status is tdm_open or permission_granted can contribute numbers.
  * n_eff counts independent first-hand accounts: duplicates, retellings and second-hand
    accounts are removed; one representative per cluster.
  * A claim is 'confirmed' only with independent_document or independent_witness evidence.
    Anything else marked confirmed is counted as unverifiable and flagged.
  * Motif frequencies and the checkable-claim rate always carry a 95% Wilson interval.
  * For questionnaire sources (items_answered present) the denominator of each item is the number
    of accounts that answered it; "uncertain" answers stay in the denominator and are listed.
  * The headline group is the accounts the source itself classifies as "NDE" (classification.group).
  * Health cases are counted per documentation level, never pooled, and only when a human
    reviewed them.
  * Sources with public=false are published as "Source N" without name or link.

Usage: py scripts/testimony_status.py [--root .] [--data DIR] [--out FILE]
Standard library only.
"""
import argparse
import datetime
import json
import math
import os
import sys

ALLOWED = {"tdm_open", "permission_granted"}
FIRST_HAND = {"first_hand", "interview_transcript"}
INDEPENDENT = {"independent_document", "independent_witness"}
KAPPA_LOW = 0.6


def wilson(k, n, z=1.96):
    """95% Wilson score interval for k successes out of n. Returns [lo, hi] in percent."""
    if n <= 0:
        return None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(max(0.0, centre - half) * 100, 1), round(min(1.0, centre + half) * 100, 1)]


def load_records(path, warnings):
    out = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError as exc:
                warnings.append("%s line %d: invalid JSON (%s)" % (os.path.basename(path), i, exc))
    return out


def representatives(records):
    """One representative per independent first-hand account."""
    seen, reps = set(), []
    for r in records:
        if r.get("account_type") not in FIRST_HAND:
            continue
        dup = r.get("duplicates") or {}
        if dup.get("duplicate_of"):
            continue
        if dup.get("method") == "retelling":
            continue
        key = dup.get("cluster_id") or r.get("id")
        if key in seen:
            continue
        seen.add(key)
        reps.append(r)
    return reps


def motif_codes(rec):
    codes = {}
    for m in rec.get("motifs") or []:
        code = m.get("code")
        if not code:
            continue
        # a human code overrides an LLM code for the same motif
        if code not in codes or m.get("coder") == "human":
            codes[code] = m.get("coder")
    return codes


def group_of(rec):
    return (rec.get("classification") or {}).get("group")


def analyse(records, reliability, warnings, labels=None):
    labels = labels or {}
    reps_all = representatives(records)
    groups = {}
    for r in reps_all:
        g = group_of(r) or "nde"
        groups[g] = groups.get(g, 0) + 1
    # headline group: records classified "nde" by the source when classification is recorded
    has_cls = any(group_of(r) for r in reps_all)
    reps = [r for r in reps_all if (group_of(r) or "nde") == "nde"] if has_cls else reps_all
    n_eff = len(reps)
    res = {"n_raw": len(records), "n_eff": len(reps_all), "n_headline": n_eff,
           "headline_group": "nde" if has_cls else "all", "groups": groups}
    if not n_eff:
        res.update({"motifs": [], "checkable": None, "verification": None, "verification_downgraded": 0,
                    "health_cases_by_documentation_level": {}, "health_cases_awaiting_human_review": 0})
        return res

    structured = any("items_answered" in r for r in reps)
    counts, denom, unc, coders = {}, {}, {}, {}
    for r in reps:
        mc = motif_codes(r)
        for c, cd in mc.items():
            counts[c] = counts.get(c, 0) + 1
            coders.setdefault(c, set()).add(cd)
        for c in (r.get("items_answered") or []):
            denom[c] = denom.get(c, 0) + 1
        for c in (r.get("items_uncertain") or []):
            unc[c] = unc.get(c, 0) + 1
    for c in denom:
        counts.setdefault(c, 0)
    motifs = []
    for code, k in counts.items():
        den = denom.get(code, 0) if structured else n_eff
        if not den:
            continue
        by_rule = coders.get(code, {"rule"}) == {"rule"} if code in coders else bool(structured)
        kappa = reliability.get(code)
        lab = labels.get(code) or {}
        motifs.append({
            "code": code, "label": {"en": lab.get("en", code), "lv": lab.get("lv", code)},
            "count": k, "n": den, "uncertain": unc.get(code, 0),
            "percent": round(k / den * 100, 1), "ci95": wilson(k, den),
            "coding": "rule" if by_rule else "model_or_human",
            "kappa": kappa,
            "low_reliability": (not by_rule and kappa is not None and kappa < KAPPA_LOW),
            "reliability_checked": by_rule or kappa is not None,
        })
    motifs.sort(key=lambda m: (-m["percent"], m["code"]))
    res["motifs"] = motifs

    with_checkable, verif = 0, {"confirmed": 0, "refuted": 0, "unverifiable": 0, "not_attempted": 0}
    downgraded = 0
    for r in reps:
        claims = [c for c in (r.get("claims") or []) if c.get("checkable")]
        if claims:
            with_checkable += 1
        for c in claims:
            v = c.get("verification") or {}
            status = v.get("status", "not_attempted")
            if status == "confirmed" and v.get("evidence_type") not in INDEPENDENT:
                status = "unverifiable"
                downgraded += 1
            verif[status] = verif.get(status, 0) + 1
    res["checkable"] = {"accounts_with_checkable_claim": with_checkable,
                        "percent": round(with_checkable / n_eff * 100, 1) if n_eff else None,
                        "ci95": wilson(with_checkable, n_eff)}
    res["verification"] = verif
    res["verification_downgraded"] = downgraded
    if downgraded:
        warnings.append("%d claim(s) marked confirmed without independent evidence were counted as unverifiable" % downgraded)

    levels, unreviewed = {}, 0
    for r in reps_all:
        mc = r.get("medical_case")
        if not mc:
            continue
        if not mc.get("reviewed_by_human"):
            unreviewed += 1
            continue
        lv = mc.get("documentation_level", "unknown")
        levels[lv] = levels.get(lv, 0) + 1
    res["health_cases_by_documentation_level"] = levels
    res["health_cases_awaiting_human_review"] = unreviewed
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = a.root
    data_dir = a.data or os.path.join(root, "narrative_corpus", "data")
    out_path = a.out or os.path.join(root, "content", "articles", "testimony_status.json")
    src_path = os.path.join(root, "narrative_corpus", "sources.json")

    with open(src_path, encoding="utf-8") as fh:
        sources = json.load(fh)["sources"]

    warnings = []
    reliability = {}
    rel_path = os.path.join(data_dir, "reliability.json")
    if os.path.exists(rel_path):
        with open(rel_path, encoding="utf-8") as fh:
            reliability = json.load(fh)

    labels = {}
    cb_path = os.path.join(root, "narrative_corpus", "codebook.json")
    if os.path.exists(cb_path):
        with open(cb_path, encoding="utf-8") as fh:
            for it in json.load(fh).get("items", []):
                labels[it["code"]] = {"en": it.get("label_en"), "lv": it.get("label_lv")}

    all_included = []
    out_sources = []
    for n, s in enumerate(sources, 1):
        key = s["key"]
        path = os.path.join(data_dir, key + ".jsonl")
        recs = load_records(path, warnings) if os.path.exists(path) else []
        allowed = s.get("access_status") in ALLOWED
        if recs and not allowed:
            warnings.append("%s has %d record(s) but access_status is %s: ignored" % (key, len(recs), s.get("access_status")))
            recs_used = []
        else:
            recs_used = recs
        public = bool(s.get("public"))
        entry = {
            "name": s["display_name"] if public else "Source %d" % n,
            "url": s.get("url") if public else None,
            "public": public,
            "kind": s.get("kind"),
            "access_status": s.get("access_status"),
            "permission": s.get("permission"),
            "included_in_numbers": bool(allowed and recs_used),
            "n_raw": len(recs_used),
            "n_eff": len(representatives(recs_used)) if recs_used else 0,
        }
        if public:
            entry["kind_note"] = s.get("kind_note")
        out_sources.append(entry)
        if allowed:
            all_included.extend(recs_used)

    pooled = analyse(all_included, reliability, warnings, labels) if all_included else {
        "n_raw": 0, "n_eff": 0, "n_headline": 0, "headline_group": None, "groups": {}, "motifs": [], "checkable": None, "verification": None,
        "verification_downgraded": 0, "health_cases_by_documentation_level": {},
        "health_cases_awaiting_human_review": 0}

    status = "no_data"
    if pooled["n_eff"] > 0 and pooled.get("n_headline", pooled["n_eff"]) > 0:
        status = "measured"
    elif any((s.get("permission") or {}).get("state") == "granted" for s in sources):
        status = "permission_granted_no_data"

    result = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "summary": {
            "candidate_sources": len(sources),
            "permission_granted_or_open": sum(1 for s in sources if s.get("access_status") in ALLOWED),
            "awaiting_reply": sum(1 for s in sources if (s.get("permission") or {}).get("state") == "requested"),
            "not_yet_requested": sum(1 for s in sources if (s.get("permission") or {}).get("state") == "not_requested"),
            "sources_with_numbers": sum(1 for s in out_sources if s["included_in_numbers"]),
        },
        "sources": out_sources,
        "pooled": pooled,
        "warnings": warnings,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("testimony_status: status=%s n_raw=%d n_eff=%d sources=%d -> %s" % (
        status, pooled["n_raw"], pooled["n_eff"], len(sources), out_path))
    for w in warnings:
        print("  warning:", w, file=sys.stderr)


if __name__ == "__main__":
    main()
