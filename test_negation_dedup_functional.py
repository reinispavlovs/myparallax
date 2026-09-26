import sys
import json
from pathlib import Path

root = Path(".").resolve()
sys.path.insert(0, str(root))

from scripts.shared.claim_layers_utils import validate_content_flags

promoted_dir = root / "drafts" / "_promoted"
drafts_dir = root / "drafts"

candidates = []
if promoted_dir.exists():
    candidates.extend(sorted(promoted_dir.glob("*.meta.json")))
candidates.extend(sorted(drafts_dir.glob("*.meta.json")))

print(f"Found {len(candidates)} meta.json files to test.\n")

for meta_path in candidates:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    topic_id = meta.get("topic_id", "UNKNOWN")
    stored_flags = meta.get("content_flags", [])
    layers = meta.get("claim_layers", [])

    recomputed = []
    for layer in layers:
        recomputed.extend(validate_content_flags(layer))
    recomputed_deduped = list(dict.fromkeys(recomputed))

    print("=" * 70)
    print(f"Topic: {topic_id}")
    print(f"File: {meta_path.name}")
    print(f"Stored flags (old logic):      {stored_flags}")
    print(f"Recomputed (raw, new logic):   {recomputed}")
    print(f"Recomputed (deduped):          {recomputed_deduped}")

    has_084 = any("0.84" in f for f in recomputed)
    dup_check = len(recomputed) != len(set(recomputed))
    print(f"  -> 0.84 still flagged?  {has_084}")
    print(f"  -> Raw duplicates present in recompute? {dup_check}")
    print()
