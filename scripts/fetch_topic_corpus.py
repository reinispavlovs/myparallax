import os, json, time, requests

SS_URL = 'https://api.semanticscholar.org/graph/v1/paper/search'
ES_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
SUM_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
FETCH_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'

def _load_queries(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get('queries', data.get('query_variants', []))
    if isinstance(data, list):
        return data
    return []

def _search_ss(query, max_results=15):
    out = []
    headers = {}
    key = os.getenv('SEMANTIC_SCHOLAR_API_KEY')
    if key:
        headers['x-api-key'] = key
    params = {'query': query, 'limit': max_results, 'fields': 'title,abstract,year,authors,url'}
    try:
        r = requests.get(SS_URL, params=params, headers=headers, timeout=20)
        if r.status_code == 200:
            for p in r.json().get('data', []):
                out.append({'title': p.get('title') or '', 'abstract': p.get('abstract') or '', 'year': p.get('year'), 'authors': [a.get('name') for a in (p.get('authors') or [])], 'url': p.get('url') or '', 'source': 'semantic_scholar'})
        else:
            print('  [warn] SemanticScholar status', r.status_code, 'for', query)
    except Exception as e:
        print('  [warn] SemanticScholar error:', e)
    return out

def _fetch_pubmed_abstract(pmid):
    try:
        params = {'db': 'pubmed', 'id': pmid, 'rettype': 'abstract', 'retmode': 'text'}
        r = requests.get(FETCH_URL, params=params, timeout=20)
        if r.status_code == 200:
            r.encoding = r.apparent_encoding or 'utf-8'
            if r.text.strip():
                return r.text.strip()
    except Exception:
        pass
    return ''

def _search_pubmed(query, max_results=15):
    out = []
    try:
        params = {'db': 'pubmed', 'term': query, 'retmax': max_results, 'retmode': 'json'}
        r = requests.get(ES_URL, params=params, timeout=20)
        if r.status_code != 200:
            print('  [warn] PubMed esearch status', r.status_code, 'for', query)
            return out
        ids = r.json().get('esearchresult', {}).get('idlist', [])
        if not ids:
            return out
        sp = {'db': 'pubmed', 'id': ','.join(ids), 'retmode': 'json'}
        rs = requests.get(SUM_URL, params=sp, timeout=20)
        summaries = {}
        if rs.status_code == 200:
            res = rs.json().get('result', {})
            for uid in res.get('uids', []):
                summaries[uid] = res.get(uid, {})
        for pmid in ids:
            info = summaries.get(pmid, {})
            title = info.get('title', '')
            abstract = _fetch_pubmed_abstract(pmid)
            out.append({'title': title, 'abstract': abstract, 'year': (info.get('pubdate') or '')[:4], 'authors': [a.get('name') for a in info.get('authors', [])] if info.get('authors') else [], 'url': 'https://pubmed.ncbi.nlm.nih.gov/' + str(pmid) + '/', 'source': 'pubmed'})
            time.sleep(0.34)
    except Exception as e:
        print('  [warn] PubMed error:', e)
    return out

def build_corpus(topic_name, query_variants_file, max_per_query=15, verbose=True):
    queries = _load_queries(query_variants_file)
    if not queries:
        if verbose:
            print('  [warn] no queries in', query_variants_file)
        return []
    all_entries = []
    seen = set()
    for q in queries:
        if verbose:
            print('  -> querying:', q)
        for entry in _search_ss(q, max_per_query):
            k = entry['title'].strip().lower()
            if k and k not in seen:
                seen.add(k)
                all_entries.append(entry)
        for entry in _search_pubmed(q, max_per_query):
            k = entry['title'].strip().lower()
            if k and k not in seen:
                seen.add(k)
                all_entries.append(entry)
        time.sleep(0.5)
    if verbose:
        print('  [' + topic_name + '] corpus built:', len(all_entries), 'unique entries')
    return all_entries

