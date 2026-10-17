#!/usr/bin/env python3
"""Build the weekly briefing from the site's own published data. No model, no API, no network.

Reads   content/articles/{topic_weights,index,corrections,archive,testimony_status}.json
        content/weekly/state.json   (numbers from the previous run, for the week-on-week diff)
Writes  content/weekly/latest.json  (text + items + numbers; the home page player reads this)
        content/weekly/latest.txt   (plain text for the speech step)
        content/weekly/state.json   (new snapshot)
        content/weekly/history.json (last 12 briefings, text only)

Every sentence is a template filled with a number or a log entry that is already public.
Nothing is invented, and nothing is called proven. Standard library only.

Usage: python scripts/weekly_briefing.py [--root .] [--today YYYY-MM-DD]
"""
import argparse, datetime, json, os

SHORT = {
    "consciousness_independence_nde": "consciousness and near-death experiences",
    "megalithic_engineering_acoustics": "megalithic engineering and acoustics",
    "cyclical_cataclysms_precession": "cyclical cataclysms and precession",
    "neural_cosmic_isomorphism": "the neural and cosmic network comparison",
}


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def fmt(x):
    return ("%.1f" % x).rstrip("0").rstrip(".") if isinstance(x, (int, float)) else str(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--today", default=None)
    a = ap.parse_args()
    root = a.root
    art = os.path.join(root, "content", "articles")
    wk = os.path.join(root, "content", "weekly")
    os.makedirs(wk, exist_ok=True)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    since = today - datetime.timedelta(days=7)

    weights = (load(os.path.join(art, "topic_weights.json"), {}) or {}).get("topics", {})
    index = (load(os.path.join(art, "index.json"), {}) or {}).get("topics", {})
    corr = (load(os.path.join(art, "corrections.json"), {}) or {}).get("entries", [])
    arch = (load(os.path.join(art, "archive.json"), {}) or {}).get("versions", [])
    tm = load(os.path.join(art, "testimony_status.json"), {}) or {}
    prev = load(os.path.join(wk, "state.json"), {}) or {}

    cov = {t: w.get("percent_mapped") for t, w in weights.items()}
    cls = {t: w.get("epistemic_class") for t, w in weights.items()}
    corpus = {t: (ix.get("evidence_summary") or {}).get("analysed") for t, ix in index.items()}
    pooled = tm.get("pooled") or {}
    ver = pooled.get("verification") or {}
    state = {
        "date": today.isoformat(),
        "coverage": cov, "class": cls, "corpus_analysed": corpus,
        "testimony_n": pooled.get("n_headline"),
        "confirmed": ver.get("confirmed", 0),
    }

    items, sents = [], []
    first_run = not prev
    # 1. coverage / class changes
    for t in SHORT:
        if t not in cov:
            continue
        old, new = (prev.get("coverage") or {}).get(t), cov[t]
        if not first_run and old is not None and new is not None and abs(new - old) > 1e-9:
            s = "Checklist coverage for %s moved from %s to %s percent." % (SHORT[t], fmt(old), fmt(new))
            items.append({"kind": "coverage", "topic": t, "text": s}); sents.append(s)
        oc, nc = (prev.get("class") or {}).get(t), cls.get(t)
        if not first_run and oc and nc and oc != nc:
            s = "The epistemic class of %s changed from %s to %s." % (SHORT[t], oc, nc)
            items.append({"kind": "class", "topic": t, "text": s}); sents.append(s)
    # 2. literature corpus growth
    for t in SHORT:
        old, new = (prev.get("corpus_analysed") or {}).get(t), corpus.get(t)
        if not first_run and old and new and new != old:
            s = "The literature corpus on %s now covers %d analysed abstracts, up from %d." % (SHORT[t], new, old)
            items.append({"kind": "corpus", "topic": t, "text": s}); sents.append(s)
    # 3. testimony
    n_old, n_new = prev.get("testimony_n"), state["testimony_n"]
    if n_new and (first_run or n_old != n_new):
        s = ("The testimony layer now holds %d near-death accounts classified as such by the source." % n_new
             if first_run or not n_old else
             "The testimony layer grew from %d to %d accounts." % (n_old, n_new))
        items.append({"kind": "testimony", "text": s}); sents.append(s)
    if ver:
        s = "Independently confirmed testimony claims: %d." % ver.get("confirmed", 0)
        items.append({"kind": "verification", "text": s}); sents.append(s)
    # 4. log entries from the last 7 days (corrections and new article versions)
    new_corr = [e for e in corr if e.get("date") and since <= datetime.date.fromisoformat(e["date"]) <= today]
    if new_corr:
        topics = sorted({SHORT.get(e.get("topic"), "the whole site") for e in new_corr})
        s = "%d correction%s logged this week, affecting %s. The full log is on the page." % (
            len(new_corr), "" if len(new_corr) == 1 else "s", ", ".join(topics))
        items.append({"kind": "corrections", "text": s}); sents.append(s)
    new_ver = [v for v in arch if v.get("kind") != "current" and (v.get("published_at") or "")[:10] >= since.isoformat()]
    cur_new = [v for v in arch if v.get("kind") == "current" and (v.get("published_at") or "")[:10] >= since.isoformat()]
    nv = len(new_ver) + len(cur_new)
    if nv:
        s = "%d human-reviewed article version%s published." % (nv, "" if nv == 1 else "s")
        items.append({"kind": "versions", "text": s}); sents.append(s)

    changed = bool([i for i in items if i["kind"] in ("coverage", "class", "corpus", "corrections", "versions")]) or (
        n_old != n_new and not first_run)
    if first_run:
        sents.insert(0, "This is the first automatic briefing. Changes will be listed from next week.")
    elif not changed:
        sents.insert(0, "No status changed this week.")
    standing = [("%s, %s percent" % (SHORT[t], fmt(cov[t]))) for t in SHORT if cov.get(t) is not None]
    if standing:
        sents.append("Current checklist coverage: " + "; ".join(standing) + ".")
    head = "Project Parallax weekly briefing, %s." % today.strftime("%d %B %Y")
    tail = ("Coverage percentages measure how many testing criteria are met. They are not the probability that a claim is true. "
            "Testimony figures are self-reported accounts, not proof. This briefing was generated automatically from published data.")
    text = " ".join([head] + sents + [tail])

    out = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period": {"from": since.isoformat(), "to": today.isoformat()},
        "language": "en", "automatic": True, "changed": changed,
        "items": items, "text": text,
        "numbers": {"coverage": cov, "testimony_n": n_new, "confirmed": state["confirmed"]},
        "audio": "content/weekly/latest.mp3",
    }
    with open(os.path.join(wk, "latest.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2); fh.write("\n")
    with open(os.path.join(wk, "latest.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")
    with open(os.path.join(wk, "state.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2); fh.write("\n")
    hist = load(os.path.join(wk, "history.json"), []) or []
    hist = [h for h in hist if h.get("date") != today.isoformat()]
    hist.insert(0, {"date": today.isoformat(), "text": text})
    with open(os.path.join(wk, "history.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(hist[:12], fh, ensure_ascii=False, indent=2); fh.write("\n")
    print("weekly briefing: %d item(s), changed=%s, %d words" % (len(items), changed, len(text.split())))


if __name__ == "__main__":
    main()
