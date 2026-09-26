"""
Aizstāj fetch_arxiv_source.py loģiku ar vairāku-avotu korpusa vākšanu.
Atgriež list[dict] ar vienotu struktūru neatkarīgi no avota.
"""
import requests
import time
import json

def _normalize(paper, source):
    return {
        "source_db": source,
        "title": paper.get("title", ""),
        "abstract": paper.get("abstract", "") or "",
        "year": paper.get("year"),
        "doi": paper.get("externalIds", {}).get("DOI") if source == "semantic_scholar" else paper.get("doi"),
        "citation_count": paper.get("citationCount", 0),
        "open_access_pdf": (paper.get("openAccessPdf") or {}).get("url"),
        "authors": [a.get("name") for a in paper.get("authors", [])] if source == "semantic_scholar" else paper.get("authors", [])
    }

def search_semantic_scholar(query, limit=100):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "fields": "title,abstract,year,citationCount,openAccessPdf,externalIds,authors",
        "limit": min(limit, 100)
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return [_normalize(p, "semantic_scholar") for p in r.json().get("data", []) if p.get("abstract")]
    except Exception as e:
        print(f"[WARN] Semantic Scholar failed for '{query}': {e}")
        return []

def search_pubmed(query, retmax=100):
    esearch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    try:
        r = requests.get(esearch, params={
            "db": "pubmed", "term": query, "retmax": retmax, "retmode": "json"
        }, timeout=15)
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        esummary = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        r2 = requests.get(esummary, params={
            "db": "pubmed", "id": ",".join(ids), "retmode": "json"
        }, timeout=15)
        result = r2.json().get("result", {})
        papers = []
        for uid in ids:
            item = result.get(uid, {})
            papers.append(_normalize({
                "title": item.get("title", ""),
                "abstract": "",  # esummary nedod abstract; efetch vajadzīgs papildus
                "year": item.get("pubdate", "")[:4] if item.get("pubdate") else None,
                "doi": next((x["value"] for x in item.get("articleids", []) if x.get("idtype") == "doi"), None),
                "authors": [a.get("name") for a in item.get("authors", [])]
            }, "pubmed"))
        return papers
    except Exception as e:
        print(f"[WARN] PubMed failed for '{query}': {e}")
        return []

def dedupe(corpus):
    seen = set()
    result = []
    for paper in corpus:
        key = (paper.get("doi") or paper.get("title", "")).lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(paper)
    return result

def build_corpus(query_variants, sources=("semantic_scholar", "pubmed"), limit_per_query=100):
    corpus = []
    for q in query_variants:
        if "semantic_scholar" in sources:
            corpus += search_semantic_scholar(q, limit_per_query)
            time.sleep(1.2)  # rate-limit safety
        if "pubmed" in sources:
            corpus += search_pubmed(q, limit_per_query)
            time.sleep(0.5)
    return dedupe(corpus)

if __name__ == "__main__":
    # Manuāls tests
    variants = [
        "near-death experience veridical perception",
        "out-of-body experience verified case",
        "cardiac arrest consciousness AWARE study"
    ]
    result = build_corpus(variants)
    print(f"Corpus size after dedupe: {len(result)}")
    with open("test_corpus_output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
