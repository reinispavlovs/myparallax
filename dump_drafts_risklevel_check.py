import json
from pathlib import Path

REPO_ROOT = Path(".").resolve()
DRAFTS_DIR = REPO_ROOT / "drafts"

print("=== drafts/*.meta.json (all, incl. promoted) ===")
for mf in sorted(DRAFTS_DIR.glob("*.meta.json")):
    meta = json.loads(mf.read_text(encoding="utf-8"))
    print(f"{mf.name}")
    print(f"  topic_id={meta.get('topic_id')!r}")
    print(f"  risk_level={meta.get('risk_level')!r}")
    print(f"  promoted={meta.get('promoted')!r}")
    print(f"  promoted_at={meta.get('promoted_at')!r}")
    print(f"  credibility_score_C_i={meta.get('credibility_score_C_i')!r}")
    print()
