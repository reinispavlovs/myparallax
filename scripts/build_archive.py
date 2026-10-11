#!/usr/bin/env python3
"""
build_archive.py
----------------
Builds content/articles/archive.json: a public, append-only-in-spirit list of every
published version of every article (the current one plus everything in _history/).

Run it after promote_drafts.py (promote_drafts.py calls it automatically):
    python scripts/build_archive.py

Rules:
  * Nothing is deleted or edited. Old versions stay as they were, errors included.
  * An entry can be hidden from the public archive page by setting "hidden": true
    on it in archive.json. The flag is preserved on every rebuild.
  * "replaced_at" for an archived version is the time it was superseded (taken from
    the backup file name). The publication time of the old version is only known when a
    sidecar <backup>.meta.json exists (written by promote_drafts.py).
"""
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = REPO_ROOT / "content" / "articles"
HISTORY_DIR = ARTICLES_DIR / "_history"
ARCHIVE_PATH = ARTICLES_DIR / "archive.json"
INDEX_PATH = ARTICLES_DIR / "index.json"

HIST_RE = re.compile(r"^(?P<topic>[a-z0-9_]+)-(?P<ts>\d{8}T\d{6}Z)\.html$")
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
REVIEWED_RE = re.compile(r"human-reviewed on (\d{4}-\d{2}-\d{2})", re.I)
DRAFT_RE = re.compile(r"PENDING HUMAN FACT-CHECK", re.I)


def _load(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _inspect(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    m = H1_RE.search(text)
    title = re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", m.group(1)))).strip() if m else None
    r = REVIEWED_RE.search(text)
    if r:
        review, reviewed_on = "human_reviewed", r.group(1)
    elif DRAFT_RE.search(text):
        review, reviewed_on = "ai_draft", None
    else:
        review, reviewed_on = "unknown", None
    return title, review, reviewed_on


def _ts_iso(ts):
    return datetime.strptime(ts, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat()


def build():
    old = _load(ARCHIVE_PATH, {}) or {}
    hidden = {v.get("version_id"): bool(v.get("hidden")) for v in old.get("versions", [])}
    index = (_load(INDEX_PATH, {}) or {}).get("topics", {})
    versions = []

    # current versions
    for topic_id, ix in index.items():
        f = ARTICLES_DIR / ix.get("article_file", "")
        if not f.exists():
            continue
        title, review, reviewed_on = _inspect(f)
        vid = f"{topic_id}-current-{(ix.get('content_hash') or '')[:8]}"
        entry = {
            "topic_id": topic_id,
            "topic_name": ix.get("topic_name"),
            "version_id": vid,
            "kind": "current",
            "file": f"content/articles/{f.name}",
            "title": title,
            "review": review,
            "reviewed_on": reviewed_on,
            "published_at": ix.get("promoted_at"),
            "generated_at": ix.get("generated_at"),
            "size": f.stat().st_size,
            "credibility_score": ix.get("credibility_score"),
            "risk_level": ix.get("risk_level"),
            "evidence_summary": ix.get("evidence_summary"),
            "hidden": hidden.get(vid, False),
        }
        versions.append(entry)

    # archived versions
    if HISTORY_DIR.exists():
        for f in sorted(HISTORY_DIR.glob("*.html")):
            m = HIST_RE.match(f.name)
            if not m:
                continue
            topic_id, ts = m.group("topic"), m.group("ts")
            if topic_id not in index and not any(v["topic_id"] == topic_id for v in versions):
                pass  # keep it anyway: archive is complete
            title, review, reviewed_on = _inspect(f)
            side = _load(f.with_suffix(".meta.json"), {}) or {}
            vid = f"{topic_id}-{ts}"
            versions.append({
                "topic_id": topic_id,
                "topic_name": side.get("topic_name") or (index.get(topic_id) or {}).get("topic_name"),
                "version_id": vid,
                "kind": "archived",
                "file": f"content/articles/_history/{f.name}",
                "title": title,
                "review": review,
                "reviewed_on": reviewed_on,
                "published_at": side.get("promoted_at"),
                "generated_at": side.get("generated_at"),
                "replaced_at": _ts_iso(ts),
                "size": f.stat().st_size,
                "credibility_score": side.get("credibility_score"),
                "risk_level": side.get("risk_level"),
                "evidence_summary": side.get("evidence_summary"),
                "hidden": hidden.get(vid, False),
            })

    versions.sort(key=lambda v: (v["topic_id"], 0 if v["kind"] == "current" else 1,
                                 -(datetime.fromisoformat(v["replaced_at"]).timestamp() if v.get("replaced_at") else 0)))

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Every published version is kept unedited. Set \"hidden\": true on an entry to hide it from the archive page.",
        "versions": versions,
    }
    ARCHIVE_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    res = build()
    n_cur = sum(1 for v in res["versions"] if v["kind"] == "current")
    print(f"[OK] archive.json: {len(res['versions'])} versions ({n_cur} current, {len(res['versions']) - n_cur} archived)")
