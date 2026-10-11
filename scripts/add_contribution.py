"""Accept a reviewed study submission into the public contributions registry.

Usage (run from the project root, after you have reviewed the GitHub issue):

  py scripts\\add_contribution.py --ref 10.1016/j.resuscitation.2014.08.012 ^
      --topic consciousness_independence_nde --step 2 --stance challenges ^
      --note "One-sentence reason as agreed with the submitter" ^
      --by "Name, Affiliation" --issue 12

--ref accepts a DOI, an arXiv id/link, an ISBN or an https link. (--doi is kept as an alias.)
For a DOI the metadata comes from Crossref, then DataCite (Zenodo, OSF, arXiv DOIs).
For arXiv / ISBN / links nothing is fetched: open the link yourself, then pass
--title (and ideally --authors --year) so the public entry is correct.

What it does
  * looks a DOI up in Crossref / DataCite (title, authors, year, journal)
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


def isbn_ok(d):
    if len(d) == 10:
        try:
            return sum((10 if (c == "X" and i == 9) else int(c)) * (10 - i) for i, c in enumerate(d)) % 11 == 0
        except ValueError:
            return False
    if len(d) == 13 and d.isdigit():
        return sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(d)) % 10 == 0
    return False


def parse_ref(raw):
    t = str(raw).strip()
    doi = norm_doi(t)
    if doi:
        return {"kind": "doi", "id": doi, "url": "https://doi.org/" + doi}
    m = re.match(r"^(?:https?://arxiv\.org/(?:abs|pdf)/|arxiv:\s*)([a-z\-]+(?:\.[A-Za-z]{2})?/\d{7}|\d{4}\.\d{4,5})(v\d+)?(?:\.pdf)?/?$", t, re.I)
    if m:
        i = m.group(1) + (m.group(2) or "")
        return {"kind": "arxiv", "id": i, "url": "https://arxiv.org/abs/" + i}
    ib = re.sub(r"[\s-]", "", re.sub(r"^isbn(?:-1[03])?:?\s*", "", t, flags=re.I)).upper()
    if re.match(r"^(\d{9}[\dX]|\d{13})$", ib) and isbn_ok(ib):
        return {"kind": "isbn", "id": ib, "url": "https://openlibrary.org/isbn/" + ib}
    if re.match(r"^https://\S+$", t, re.I) and "." in urllib.parse.urlparse(t).netloc:
        return {"kind": "url", "id": t, "url": t}
    return None


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


def datacite(doi):
    url = "https://api.datacite.org/dois/" + urllib.parse.quote(doi, safe="/")
    req = urllib.request.Request(url, headers={"User-Agent": "project-parallax/1.0 (mailto:none)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        a = json.load(r)["data"]["attributes"]
    authors = ", ".join(
        (" ".join(x for x in (c.get("familyName"), (c.get("givenName") or "")[:1]) if x) or c.get("name", ""))
        for c in (a.get("creators") or [])[:4])
    pub = a.get("publisher")
    pub = pub.get("name") if isinstance(pub, dict) else (pub or "")
    return {"title": ((a.get("titles") or [{}])[0]).get("title", ""), "journal": pub,
            "year": a.get("publicationYear"), "authors": authors}


def lookup_doi(doi):
    try:
        return crossref(doi)
    except Exception:
        return datacite(doi)


def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None, fetch=lookup_doi):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", help="DOI, arXiv id/link, ISBN or https link")
    ap.add_argument("--doi", help="alias for --ref")
    ap.add_argument("--title", default="", help="required for non-DOI references")
    ap.add_argument("--authors", default="")
    ap.add_argument("--year", default="")
    ap.add_argument("--publisher", default="", help="journal / publisher (non-DOI references)")
    ap.add_argument("--topic", required=True, choices=TOPICS)
    ap.add_argument("--step", required=True, choices=STEPS)
    ap.add_argument("--stance", required=True, choices=STANCES)
    ap.add_argument("--note", required=True)
    ap.add_argument("--by", default="")
    ap.add_argument("--issue", default="")
    ap.add_argument("--reviewer-note", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    ref = parse_ref(a.ref or a.doi or "")
    if not ref:
        sys.exit("Invalid reference: use a DOI, arXiv id/link, ISBN or https link.")
    doi = ref["id"] if ref["kind"] == "doi" else ""
    reg_path, log_path = ART / "contributions.json", ART / "corrections.json"
    reg = load(reg_path, {"entries": []})
    key = lambda e: str(e.get("ref") or e.get("doi") or "").lower()
    if any(key(e) == ref["id"].lower() and e["topic"] == a.topic and str(e["step"]) == a.step
           for e in reg["entries"]):
        sys.exit("This reference is already registered for that topic and step.")

    if doi:
        meta = fetch(doi)
    else:
        if not a.title.strip():
            sys.exit("Non-DOI reference: open the link, verify it, then pass --title (and --authors --year).")
        meta = {"title": a.title.strip(), "journal": a.publisher.strip(),
                "year": int(a.year) if str(a.year).isdigit() else None, "authors": a.authors.strip()}
    n = max([int(re.sub(r"\D", "", e["id"]) or 0) for e in reg["entries"]] + [0]) + 1
    entry = {"id": "c%03d" % n, "topic": a.topic, "step": a.step if a.step == "side" else int(a.step),
             "stance": a.stance, "ref_kind": ref["kind"], "ref": ref["id"], "url": ref["url"], "doi": doi, **meta, "note": a.note.strip(),
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
              % (a.step, a.stance, meta["title"] or ref["id"], meta["authors"], meta["year"], who),
        "lv": "Pievienots ieguldīts pētījums pie soļa %s (%s): %s (%s, %s). Šis papildinājums nemaina nevienu procentu vai statusu.%s"
              % (a.step, a.stance, meta["title"] or ref["id"], meta["authors"], meta["year"], who_lv)})
    save(log_path, log)
    print("Written: contributions.json, corrections.json")
    print("REMINDER: this does not change any percentage. If the study changes a checklist criterion, "
          "edit topic_checklists.json and run scripts\\sync_checklist_percent.py.")
    return entry


if __name__ == "__main__":
    main()
