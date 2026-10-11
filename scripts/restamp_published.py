"""One-off: replace the draft banner in already-published articles with the review notice.

Run from the project root:  py scripts\\restamp_published.py
Idempotent; uses promoted_at from content/articles/index.json as the review date.
"""
import json
from pathlib import Path

from promote_drafts import stamp_review_banner  # same folder

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "content" / "articles"
index = json.loads((ART / "index.json").read_text(encoding="utf-8"))
for tid, e in index.get("topics", {}).items():
    f = ART / e["article_file"]
    date = str(e.get("promoted_at", ""))[:10] or "unknown date"
    print(f"{tid}: {'updated' if stamp_review_banner(f, date) else 'no draft banner found'}")
