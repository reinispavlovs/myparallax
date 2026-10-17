#!/usr/bin/env python3
"""Build the weekly briefing from the site's own published data. No model, no API, no network.

Reads   content/articles/{topic_weights,index,corrections,archive,testimony_status}.json
        content/weekly/state.json   (numbers from the previous run, for the week-on-week diff)
Writes  content/weekly/latest.json  (spoken text + items; the home page orb reads this)
        content/weekly/latest.txt   (the same spoken text, for the speech step)
        content/weekly/state.json   (new snapshot)
        content/weekly/history.json (last 12 briefings, text only)
        content/articles/corrections.json  (appends one automatic "data update" entry per changed figure)

The spoken text is written for the ear: short sentences, plain words, what each change means for
a reader. Every sentence is a template filled with a number or log entry that is already public.
Nothing is invented and nothing is called proven. Standard library only.

Usage: python scripts/weekly_briefing.py [--root .] [--today YYYY-MM-DD]
"""
import argparse, datetime, json, os

TOPICS = {
    "consciousness_independence_nde": {
        "en": "near-death experiences, and whether the mind can work without the brain",
        "short": "near-death experiences", "lv": "Apziņas neatkarība no smadzenēm (NDE)"},
    "megalithic_engineering_acoustics": {
        "en": "ancient stone building and its acoustics",
        "short": "ancient stone building", "lv": "Megalītiskā inženierija un akustika"},
    "cyclical_cataclysms_precession": {
        "en": "cycles of catastrophe and the wobble of the Earth's axis",
        "short": "cycles of catastrophe", "lv": "Cikliskās kataklizmas un precesija"},
    "neural_cosmic_isomorphism": {
        "en": "the comparison between brain networks and the cosmic web",
        "short": "the brain and cosmic web comparison", "lv": "Neironu tīklu un kosmiskā tīmekļa izomorfisms"},
}
NUM = {0: "none", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def fmt(x):
    return ("%.1f" % x).rstrip("0").rstrip(".") if isinstance(x, (int, float)) else str(x)


def words(n):
    return NUM.get(n, str(n))


def about(n):
    if n >= 100:
        return "about %d" % (round(n / 10.0) * 10)
    return str(n)


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
    corr_doc = load(os.path.join(art, "corrections.json"), {"entries": []}) or {"entries": []}
    corr = corr_doc.get("entries", [])
    arch = (load(os.path.join(art, "archive.json"), {}) or {}).get("versions", [])
    tm = load(os.path.join(art, "testimony_status.json"), {}) or {}
    prev = load(os.path.join(wk, "state.json"), {}) or {}

    cov = {t: w.get("percent_mapped") for t, w in weights.items()}
    cls = {t: w.get("epistemic_class") for t, w in weights.items()}
    corpus = {t: (ix.get("evidence_summary") or {}).get("analysed") for t, ix in index.items()}
    pooled = tm.get("pooled") or {}
    ver = pooled.get("verification") or {}
    n_new, n_old = pooled.get("n_headline"), prev.get("testimony_n")
    confirmed = ver.get("confirmed", 0)
    state = {"date": today.isoformat(), "coverage": cov, "class": cls, "corpus_analysed": corpus,
             "testimony_n": n_new, "confirmed": confirmed}
    first_run = not prev

    items, log, changes, meaning = [], [], [], []   # items: for json, log: public log entries

    def add_log(topic, en, lv):
        log.append({"date": today.isoformat(), "topic": topic, "en": en, "lv": lv, "kind": "data", "auto": True})

    for t, info in TOPICS.items():
        old, new = (prev.get("coverage") or {}).get(t), cov.get(t)
        if not first_run and old is not None and new is not None and abs(new - old) > 1e-9:
            changes.append("The share of tests met for %s moved from %s to %s percent." % (info["short"], fmt(old), fmt(new)))
            items.append({"kind": "coverage", "topic": t})
            add_log(t, "Checklist coverage for this topic changed from %s%% to %s%% (automatic data update)." % (fmt(old), fmt(new)),
                    "Kontrolsaraksta segums šai tēmai mainījies no %s%% uz %s%% (automātisks datu atjauninājums)." % (fmt(old), fmt(new)))
        oc, nc = (prev.get("class") or {}).get(t), cls.get(t)
        if not first_run and oc and nc and oc != nc:
            changes.append("The evidence class for %s changed from %s to %s." % (info["short"], oc, nc))
            items.append({"kind": "class", "topic": t})
            add_log(t, "Epistemic class changed from %s to %s (automatic data update)." % (oc, nc),
                    "Epistēmiskā klase mainīta no %s uz %s (automātisks datu atjauninājums)." % (oc, nc))
        old, new = (prev.get("corpus_analysed") or {}).get(t), corpus.get(t)
        if not first_run and old and new and new != old:
            changes.append("We read more research papers on %s. The count is now %d, up from %d." % (info["short"], new, old))
            items.append({"kind": "corpus", "topic": t})
            add_log(t, "Literature corpus size changed from %d to %d analysed abstracts (automatic data update)." % (old, new),
                    "Literatūras korpusa apjoms mainīts no %d uz %d analizētiem abstraktiem (automātisks datu atjauninājums)." % (old, new))
    if not first_run and n_old and n_new and n_new != n_old:
        added = n_new - n_old
        changes.append("We added %s more personal accounts of near-death experiences." % (about(added) if added >= 100 else str(added)) if added > 0
                       else "The number of personal accounts changed after a data fix.")
        items.append({"kind": "testimony"})
        add_log("consciousness_independence_nde", "Testimony layer changed from %d to %d accounts (automatic data update)." % (n_old, n_new),
                "Liecību slānis mainīts no %d uz %d stāstiem (automātisks datu atjauninājums)." % (n_old, n_new))
    new_corr = [e for e in corr if e.get("date") and since <= datetime.date.fromisoformat(e["date"]) <= today and not e.get("auto")]
    if new_corr:
        k = len(new_corr)
        changes.append("We fixed %s thing%s in public. The list of fixes is on the home page." % (words(k), "" if k == 1 else "s"))
        items.append({"kind": "corrections"})
    nv = len([v for v in arch if (v.get("published_at") or "")[:10] >= since.isoformat() and v.get("review") == "human_reviewed"])
    if nv:
        changes.append("%s article%s got a new version checked by a person." % (words(nv).capitalize(), "" if nv == 1 else "s"))
        items.append({"kind": "versions"})

    kinds = {i["kind"] for i in items}
    if "coverage" in kinds or "class" in kinds:
        meaning.append("A higher score means more of the checks are done. It does not mean the claim is more likely to be true.")
    if "testimony" in kinds:
        meaning.append("More stories make the picture clearer, but stories alone cannot prove anything.")
    if "corrections" in kinds:
        meaning.append("You can see exactly what we got wrong and what we fixed.")
    if "corpus" in kinds:
        meaning.append("A bigger reading list makes the summary harder to cherry-pick.")
    if first_run:
        meaning.append("You get a map of where the evidence is solid, where it is thin, and what would settle each question, so you do not have to dig through the site.")
    if not meaning:
        meaning.append("A quiet week is normal. Good evidence moves slowly, and nothing here changes without a reason.")

    standing = []
    ordinals = ["First", "Next", "Then", "Last"]
    for t, info in TOPICS.items():
        w = weights.get(t)
        if not w:
            continue
        total, sat, par = w.get("total_checklist_items"), w.get("satisfied_count"), w.get("partial_count")
        if total is None or sat is None:
            continue
        lead = ordinals[min(len(standing), 3)]
        s = "%s, %s. %s of the %s checks %s fully met" % (
            lead, info["en"], words(sat).capitalize(), words(total), "is" if sat == 1 else "are")
        if par:
            s += ", and %s more %s partly met" % (words(par), "is" if par == 1 else "are")
        standing.append(s + ".")
    testimony_line = ""
    if n_new:
        testimony_line = ("We also collect personal stories of near-death experiences. There are %s so far. They are people's own reports, not proof, "
                          "and %s have been independently confirmed." % (about(n_new), "none" if not confirmed else words(confirmed)))

    sp = ["Hello, and welcome to this week's update from Project Parallax."]
    if first_run:
        sp.append("This is the first automatic update, so here is where things stand.")
    elif changes:
        sp.append("Here is what changed this week.")
        sp.extend(changes)
    else:
        sp.append("Nothing changed this week, so here is where things stand.")
    if first_run or not changes:
        sp.extend(standing)
        if testimony_line:
            sp.append(testimony_line)
    elif testimony_line and "testimony" not in kinds:
        pass
    sp.append("What this gives you: " + " ".join(meaning))
    sp.append("One thing to remember. These numbers show how much has been checked, not whether something is true. "
              "Open the Tribunal page on the website to see the details for yourself. Thanks for listening.")
    text = " ".join(sp)

    out = {"generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "period": {"from": since.isoformat(), "to": today.isoformat()},
           "language": "en", "automatic": True, "changed": bool(changes), "items": items, "text": text,
           "audio": "content/weekly/latest.mp3"}
    for name, obj in (("latest.json", out), ("state.json", state)):
        with open(os.path.join(wk, name), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2); fh.write("\n")
    with open(os.path.join(wk, "latest.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")
    hist = load(os.path.join(wk, "history.json"), []) or []
    hist = [h for h in hist if h.get("date") != today.isoformat()]
    hist.insert(0, {"date": today.isoformat(), "text": text})
    with open(os.path.join(wk, "history.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(hist[:12], fh, ensure_ascii=False, indent=2); fh.write("\n")

    if log:
        have = {(e.get("date"), e.get("topic"), e.get("en")) for e in corr}
        fresh = [e for e in log if (e["date"], e["topic"], e["en"]) not in have]
        if fresh:
            corr_doc["entries"] = fresh + corr
            with open(os.path.join(art, "corrections.json"), "w", encoding="utf-8", newline="\n") as fh:
                json.dump(corr_doc, fh, ensure_ascii=False, indent=2); fh.write("\n")
    print("weekly briefing: %d change(s), %d log entr%s, %d words" % (len(changes), len(log), "y" if len(log) == 1 else "ies", len(text.split())))


if __name__ == "__main__":
    main()
