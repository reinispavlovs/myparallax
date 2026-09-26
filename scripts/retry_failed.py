"""
retry_failed.py
Utilītprogramma, kas atkārtoti apstrādā TIKAI tos topikus,
kuri iepriekšējā main.py palaišanā beidzās ar kļūdu.

Lieto: python retry_failed.py
Atrodas: scripts/ mapē.
main.py atrodas VIENU mapi augstāk (Project Parallax/main.py).
"""

import json
import sys
from pathlib import Path

# scripts/ atrodas šeit -> SCRIPT_DIR
# main.py atrodas vienu mapi augstāk -> REPO_ROOT_DIR
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT_DIR))

from main import TOPICS, process_topic, log_failed_topic, FAILED_LOG_PATH


def load_failed_topics():
    if not FAILED_LOG_PATH.exists():
        print(f"[retry_failed] Fails nav atrasts: {FAILED_LOG_PATH}")
        return []
    try:
        data = json.loads(FAILED_LOG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("[retry_failed] failed_topics.json tukšs vai bojāts.")
        return []
    return data if isinstance(data, list) else []


def save_failed_topics(entries):
    FAILED_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    FAILED_LOG_PATH.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_unique_failed_topic_ids(entries):
    ids = set()
    for entry in entries:
        tid = entry.get("topic_id")
        if tid:
            ids.add(tid)
    return ids


def find_topic_by_id(topic_id):
    for topic in TOPICS:
        if topic.get("id") == topic_id:
            return topic
    return None


def main():
    print("=" * 60)
    print("RETRY_FAILED.PY — atkārtota neizdevušos topiku apstrāde")
    print("=" * 60)

    failed_entries = load_failed_topics()
    if not failed_entries:
        print("[retry_failed] Nav neizdevušos topiku. Viss kārtībā.")
        return

    failed_ids = get_unique_failed_topic_ids(failed_entries)
    print(f"[retry_failed] Atrasti {len(failed_ids)} unikāli topiki: {failed_ids}")

    resolved_ids = []
    still_failing_ids = []

    for topic_id in failed_ids:
        topic = find_topic_by_id(topic_id)
        if not topic:
            print(f"[retry_failed] BRĪDINĀJUMS: '{topic_id}' nav atrodams TOPICS sarakstā (iespējams, mainīts).")
            continue

        print(f"\n[retry_failed] Mēģinu atkārtoti: {topic['name']}")
        try:
            process_topic(topic)
            print(f"[retry_failed] SEKMĪGI: {topic_id}")
            resolved_ids.append(topic_id)
        except Exception as e:
            print(f"[retry_failed] ATKĀRTOTA KĻŪDA: {topic_id} -> {e}")
            log_failed_topic(topic, e)  # izmanto to pašu funkciju, kas main.py
            still_failing_ids.append(topic_id)

    # Notīra failed_topics.json — noņem VISUS ierakstus par atrisinātiem topikiem
    # (arī vecos, lai log nepieaug bezgalīgi par jau atrisinātām problēmām)
    updated_entries = load_failed_topics()
    cleaned = [
        e for e in updated_entries
        if e.get("topic_id") not in resolved_ids
    ]
    save_failed_topics(cleaned)

    print("\n" + "=" * 60)
    print(f"KOPSAVILKUMS: {len(resolved_ids)} atrisināti, {len(still_failing_ids)} vēl neizdodas.")
    if resolved_ids:
        print(f"  ✅ {resolved_ids}")
    if still_failing_ids:
        print(f"  ❌ {still_failing_ids}")
    print("=" * 60)


if __name__ == "__main__":
    main()
