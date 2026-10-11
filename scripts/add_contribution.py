"""Accept a reviewed study submission into the public contributions registry.

Usage (run from the project root, after you have reviewed the GitHub issue):

  py scripts\\add_contribution.py --doi 10.1016/j.resuscitation.2014.08.012 ^
      --topic consciousness_independence_nde --step 2 --stance challenges ^
      --note "One-sentence reason as agreed with the submitter" ^
      --by "Name, Affiliation" --issue 12

What it does
  * looks the DOI up in Crossref (title, authors, year, journal)
  * appends an 'accepted' entry to content/articles/contributions.json
  * appends a line to content/articles/corrections.json (the public log)

What it does NOT do
  * it never changes a percentage or a checklist status. If the study changes a
    criterion, edit content/articles/topic_checklists.json yourself, run
    scripts\\sync_checklist_percent.py, and mention the study in the log text.
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "content" / "articles"
TOPICS = ["consciousness_independence_nde", "megalithic_engineering_acoustics",
          "cyclical_cataclysms_precession", "neural_cosmic_isomorphism"]
STEPS = ["1", "2", "3", "4", "side"]
STANCES = ["supports", "challenges", "context"]


def norm_doi(raw):
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", str(raw).strip(), flags=re.I)
    d = re.sub(r"^doi:\s*", "", d, flags=re.I).strip()
    return d if re.match(r"^10\.\d{4,9}/\S+$", d, re.I) else None


def crossref(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    req = urllib.request.Request(url, headers={"User-Agent": "project-parallax/1.0 (mailto:none)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        m = json.load(r)["message"]
    year = ((m.get("issued") or {}).get("date-parts") or [[None]])[0][0]
    authors = ", ".join(
        " ".join(x for x in (a.get("family"), (a.get("given") or "")[:1]) if x)
        for a in (m.get("author") or [])[:4])
    return {"title": (m.get("title") or [""])[0],
            "journal": (m.get("container-title") or [""])[0],
            "year": year, "authors": authors}


def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None, fetch=crossref):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doi", required=True)
    ap.add_argument("--topic", required=True, choices=TOPICS)
    ap.add_argument("--step", required=True, choices=STEPS)
    ap.add_argument("--stance", required=True, choices=STANCES)
    ap.add_argument("--note", required=True)
    ap.add_argument("--by", default="")
    ap.add_argument("--issue", default="")
    ap.add_argument("--reviewer-note", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    doi = norm_doi(a.doi)
    if not doi:
        sys.exit("Invalid DOI.")
    reg_path, log_path = ART / "contributions.json", ART / "corrections.json"
    reg = load(reg_path, {"entries": []})
    if any(e["doi"].lower() == doi.lower() and e["topic"] == a.topic and str(e["step"]) == a.step
           for e in reg["entries"]):
        sys.exit("This DOI is already registered for that topic and step.")

    meta = fetch(doi)
    n = max([int(re.sub(r"\D", "", e["id"]) or 0) for e in reg["entries"]] + [0]) + 1
    entry = {"id": "c%03d" % n, "topic": a.topic, "step": a.step if a.step == "side" else int(a.step),
             "stance": a.stance, "doi": doi, **meta, "note": a.note.strip(),
             "contributor": a.by.strip(), "date": date.today().isoformat(), "status": "accepted",
             "reviewer_note": a.reviewer_note.strip(), "issue": a.issue}
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    if a.dry_run:
        print("[dry-run] nothing written")
        return entry

    reg["entries"].append(entry)
    save(reg_path, reg)

    log = load(log_path, {"entries": []})
    who = (" Contributed by " + a.by.strip() + ".") if a.by.strip() else ""
    who_lv = (" Pievienoja " + a.by.strip() + ".") if a.by.strip() else ""
    log["entries"].insert(0, {
        "date": entry["date"], "topic": a.topic,
        "en": "Contributed study added under step %s (%s): %s (%s, %s). No percentage or status was changed by this addition.%s"
              % (a.step, a.stance, meta["title"] or doi, meta["authors"], meta["year"], who),
        "lv": "Pievienots ieguldīts pētījums pie soļa %s (%s): %s (%s, %s). Šis papildinājums nemaina nevienu procentu vai statusu.%s"
              % (a.step, a.stance, meta["title"] or doi, meta["authors"], meta["year"], who_lv)})
    save(log_path, log)
    print("Written: contributions.json, corrections.json")
    print("REMINDER: this does not change any percentage. If the study changes a checklist criterion, "
          "edit topic_checklists.json and run scripts\\sync_checklist_percent.py.")
    return entry


if __name__ == "__main__":
    main()
