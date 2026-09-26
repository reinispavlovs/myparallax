import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

from main import TOPICS, fetch_real_arxiv_summary

print("=" * 70)
for topic in TOPICS:
    print(f"\n[TOPIC] {topic['id']}")
    print(f"  Query: {topic['arxiv_query']}")
    result = fetch_real_arxiv_summary(topic["arxiv_query"])
    print(f"  Found: {result['found']}")
    if result["found"]:
        print(f"  Overlap count: {result.get('relevance_overlap_count')}")
        print(f"  Overlap ratio: {result.get('relevance_overlap_ratio')}")
        print(f"  Text (first 150 chars): {result['text'][:150]}...")
    else:
        print(f"  Note: {result.get('note')}")
    print("-" * 70)
