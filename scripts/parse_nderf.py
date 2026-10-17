#!/usr/bin/env python3
"""Turn the private NDERF page copies into derived, text-free records.

Reads   narrative_corpus_private/nderf/raw/*.txt   (private, never published)
        narrative_corpus_private/nderf/index.jsonl (for the text hash)
        narrative_corpus/codebook.json             (questionnaire items and answer rules)
Writes  narrative_corpus/data/NDERF.jsonl          (one record per account: codes only, no text, no names)

Usage:  py scripts\\parse_nderf.py
Rules:  no free text, no excerpt, no name is copied. Only the closed-ended questionnaire answers,
        read by rule. 'Uncertain' and unmatched answers are not counted as positive.
        NDERF's own classification is kept; the headline group is the classification "NDE" only.
Standard library only.
"""
import argparse, datetime, json, os, re

QMARK = re.compile(r"^(.*?\?)\s*(.*)$")


def norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "'").strip().lower()).rstrip(".")


def words(s):
    return re.sub(r"[^a-z0-9 ]+", " ", norm(s)).split()


def stem_match(question, stem):
    """Stem words must appear in order, starting at the first word, with at most 25 extra words.
    Tolerates commas, brackets and small wording additions between questionnaire versions."""
    q, st = words(question), words(stem)
    if not st or len(q) < len(st) or len(q) > len(st) + 25 or q[0] != st[0]:
        return False
    k = 0
    for w in q:
        if w == st[k]:
            k += 1
            if k == len(st):
                return True
    return False


def classify(raw):
    n = re.sub(r"[^A-Z]", "", raw.upper())
    return "nde" if n in ("NDE", "NDES") else "other"


def parse_one(text, items):
    m = re.search(r"Classification\s+(.+)", text)
    cls_raw = m.group(1).strip() if m else ""
    i = text.find("NDE Elements")
    j = text.find("©1998")
    body = text[i:j] if i >= 0 else ""
    answers = {}
    for line in body.split("\n"):
        mm = QMARK.match(line.strip())
        if not mm:
            continue
        q, a = mm.group(1), norm(mm.group(2))
        for it in items:
            if stem_match(q, it["stem"]) and it["code"] not in answers:
                answers[it["code"]] = a
    pos, neg, unc, answered = [], [], [], []
    for it in items:
        a = answers.get(it["code"])
        if a is None or a == "":
            continue
        if a.startswith("uncertain"):
            unc.append(it["code"]); answered.append(it["code"]); continue
        if any(a.startswith(p) for p in it["positive"]):
            pos.append(it["code"]); answered.append(it["code"])
        elif any(a.startswith(n) for n in it["negative"]) or a.startswith("neither"):
            neg.append(it["code"]); answered.append(it["code"])
    claims = []
    a = answers.get("aware_elsewhere", "")
    if a.startswith("yes"):
        checked = "have been checked" in a
        claims.append({
            "claim_id": "aware_elsewhere", "type": "veridical_perception",
            "description": "Narrator reports awareness of events elsewhere (questionnaire answer).",
            "checkable": True,
            "verification": {
                "status": "unverifiable" if checked else "not_attempted",
                "evidence_type": "same_narrator_only" if checked else "none",
                "note": "Narrator states the facts were checked; not independently verified by this project." if checked else None}})
    return cls_raw, pos, answered, unc, claims, bool(body), answers, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--diag", action="store_true", help="write private per-era coverage diagnostics")
    a = ap.parse_args()
    root = a.root
    raw_dir = os.path.join(root, "narrative_corpus_private", "nderf", "raw")
    idx_path = os.path.join(root, "narrative_corpus_private", "nderf", "index.jsonl")
    cb = json.load(open(os.path.join(root, "narrative_corpus", "codebook.json"), encoding="utf-8"))
    items = cb["items"]
    meta = {}
    if os.path.exists(idx_path):
        for line in open(idx_path, encoding="utf-8"):
            try:
                r = json.loads(line); meta[r["id"]] = r
            except Exception:
                pass
    out_dir = os.path.join(root, "narrative_corpus", "data")
    os.makedirs(out_dir, exist_ok=True)
    today = datetime.date.today().isoformat()
    n = skipped = 0
    groups = {}
    diag_q = {}      # normalised question -> {era: count}
    diag_cov = {}    # code -> {era: [stories_with_item_answered, stories]}
    diag_unm = {}    # code -> {first three words of unmatched answers: count}
    def era(y):
        try:
            y = int(y)
        except Exception:
            return "?"
        return "<=2008" if y <= 2008 else ("2009-2016" if y <= 2016 else "2017+")
    with open(os.path.join(out_dir, "NDERF.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for fn in sorted(os.listdir(raw_dir)):
            if not fn.endswith(".txt"):
                continue
            rid = fn[:-4]
            text = open(os.path.join(raw_dir, fn), encoding="utf-8").read()
            cls_raw, pos, answered, unc, claims, has_q, ans, body = parse_one(text, items)
            if not has_q or not answered:
                skipped += 1
                continue
            e = era((meta.get(rid) or {}).get("archive_year"))
            for line in body.split("\n"):
                mm = QMARK.match(line.strip())
                if mm and len(mm.group(1)) < 200:
                    k = " ".join(words(mm.group(1)))
                    diag_q.setdefault(k, {}); diag_q[k][e] = diag_q[k].get(e, 0) + 1
            for it in items:
                c = diag_cov.setdefault(it["code"], {}).setdefault(e, [0, 0])
                c[1] += 1
                if it["code"] in answered:
                    c[0] += 1
                elif ans.get(it["code"]):
                    k = " ".join(norm(ans[it["code"]]).split()[:3])
                    diag_unm.setdefault(it["code"], {}); diag_unm[it["code"]][k] = diag_unm[it["code"]].get(k, 0) + 1
            grp = classify(cls_raw)
            groups[grp] = groups.get(grp, 0) + 1
            rec = {
                "id": rid,
                "source": {"name": "NDERF", "url": "https://www.nderf.org/", "retrieved_at": today, "published_at": (meta.get(rid) or {}).get("archive_year"), "access_status": "tdm_open"},
                "account_type": "first_hand",
                "collection": {"solicited": True, "delay_to_report": None},
                "text_hash": (meta.get(rid) or {}).get("text_hash"),
                "excerpt": None,
                "classification": {"raw": cls_raw, "group": grp},
                "duplicates": {"cluster_id": None, "duplicate_of": None, "method": "none"},
                "motifs": [{"code": c, "coder": "rule", "confidence": None} for c in pos],
                "items_answered": answered,
                "items_uncertain": unc,
                "claims": claims,
                "coding": {"codebook_version": cb["version"], "coder_id": "rule-parser", "coded_at": today},
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    if a.diag:
        qs = sorted(diag_q.items(), key=lambda kv: -sum(kv[1].values()))
        out = {"questions": [{"q": k, "by_era": v} for k, v in qs if sum(v.values()) >= 3],
               "coverage": diag_cov,
               "unmatched_answers": {c: {k: v for k, v in d.items() if v >= 3} for c, d in diag_unm.items()}}
        p = os.path.join(root, "narrative_corpus_private", "nderf", "diag.json")
        json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("diagnostics ->", p)
    print("records written: %d, skipped (no questionnaire): %d, groups: %s" % (n, skipped, groups))


if __name__ == "__main__":
    main()
