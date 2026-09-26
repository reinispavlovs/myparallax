"""
Klasificē katru korpusa ierakstu, tad summē statistiku.
Prasa jau esošo Gemini/LLM izsaukuma funkciju no tava pipeline (call_llm placeholder).
"""
import json

CATEGORIES = ["supports_veridical", "null_result", "neuro_mechanism", "inconclusive"]

CLASSIFY_PROMPT_TEMPLATE = """Classify the following research abstract into EXACTLY ONE category:
- supports_veridical: reports a verified/veridical anomalous perception or claim
- null_result: reports no anomaly found, or explicitly refutes such claims
- neuro_mechanism: proposes a neurological/physiological explanation without requiring non-locality
- inconclusive: theoretical, insufficient data, or ambiguous

Abstract:
\"\"\"{abstract}\"\"\"

Respond with ONLY one word from: supports_veridical, null_result, neuro_mechanism, inconclusive
"""

def classify_finding(abstract_text, call_llm_fn):
    if not abstract_text or len(abstract_text.strip()) < 20:
        return "inconclusive"
    prompt = CLASSIFY_PROMPT_TEMPLATE.format(abstract=abstract_text[:3000])
    response = call_llm_fn(prompt).strip().lower()
    for cat in CATEGORIES:
        if cat in response:
            return cat
    return "inconclusive"

def aggregate(corpus, call_llm_fn):
    tally = {c: 0 for c in CATEGORIES}
    classified_papers = []
    for paper in corpus:
        category = classify_finding(paper.get("abstract", ""), call_llm_fn)
        tally[category] += 1
        classified_papers.append({**paper, "classification": category})

    total = sum(tally.values()) or 1
    return {
        "data_type": "meta_analysis_illustrative",
        "corpus_size": len(corpus),
        "classified_total": total,
        "pct_supports_veridical": round(tally["supports_veridical"] / total * 100, 1),
        "pct_null_result": round(tally["null_result"] / total * 100, 1),
        "pct_neuro_mechanism": round(tally["neuro_mechanism"] / total * 100, 1),
        "pct_inconclusive": round(tally["inconclusive"] / total * 100, 1),
        "raw_tally": tally,
        "citation_list": [
            {
                "title": p["title"],
                "doi": p.get("doi"),
                "year": p.get("year"),
                "classification": p["classification"],
                "access_status": "open_access" if p.get("open_access_pdf") else "paywalled_or_unknown"
            }
            for p in classified_papers
        ]
    }

if __name__ == "__main__":
    with open("test_corpus_output.json", "r", encoding="utf-8") as f:
        corpus = json.load(f)

    def dummy_llm(prompt):
        return "inconclusive"  # nomaini ar reālo Gemini/LLM izsaukumu

    result = aggregate(corpus, dummy_llm)
    print(json.dumps(result, indent=2, ensure_ascii=False))
