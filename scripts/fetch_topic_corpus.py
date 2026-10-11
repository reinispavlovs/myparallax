import os, re, json, time, random, unicodedata, html, requests

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

# Per-run retrieval report, filled by build_corpus (read by callers / printed at the end of each run).
LAST_STATS = {}
_S2_LAST_CALL = [0.0]
S2_MIN_INTERVAL = 1.1      # seconds between Semantic Scholar calls (documented limit: ~1 request/second with a key)
S2_MAX_ATTEMPTS = 4
S2_CIRCUIT_AFTER = 2       # consecutive fully-failed queries before S2 is skipped for the rest of the run
_S2_FAIL_STREAK = [0]


_TITLE_PREFIX = re.compile(r'^(brief report|review article|review paper|original article|original research)\b\s*')


def _clean_title(title):
    """Unescape HTML entities and strip markup (Europe PMC returns e.g. '&lt;i&gt;Equus asinus&lt;/i&gt;')."""
    t = html.unescape(html.unescape(title or ''))
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)).strip()


def _norm_doi(doi):
    d = (doi or '').strip().lower()
    d = re.sub(r'^(https?://(dx\.)?doi\.org/|doi:)', '', d)
    return d if d.startswith('10.') else ''


def _norm_title(title):
    t = unicodedata.normalize('NFKD', _clean_title(title))
    t = ''.join(ch for ch in t if not unicodedata.combining(ch)).lower()
    t = re.sub(r'[^a-z0-9]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return _TITLE_PREFIX.sub('', t).strip()


def _find_duplicate(entry_key, seen_keys):
    """Exact match on the normalised title (case, accents, punctuation, brackets, spacing ignored).
    Fuzzy matching is deliberately NOT used: distinct papers often differ by one word
    (e.g. 'An Encounter With the Other' / 'An encounter with the self')."""
    return entry_key if entry_key in seen_keys else None


def _search_ss(query, max_results=15, stats=None):
    out = []
    if _S2_FAIL_STREAK[0] >= S2_CIRCUIT_AFTER and not (stats and stats['s2_ok']):
        print('  [warn] SemanticScholar skipped (circuit open after', _S2_FAIL_STREAK[0], 'consecutive failures):', query)
        if stats is not None:
            stats['s2_skipped'] += 1
        return out
    headers = {}
    key = os.getenv('SEMANTIC_SCHOLAR_API_KEY')
    if key:
        headers['x-api-key'] = key
    params = {'query': query, 'limit': max_results, 'fields': 'title,abstract,year,authors,url'}
    last_status = None
    for attempt in range(1, S2_MAX_ATTEMPTS + 1):
        wait = S2_MIN_INTERVAL - (time.time() - _S2_LAST_CALL[0])
        if wait > 0:
            time.sleep(wait)
        retry_after = None
        try:
            r = requests.get(SS_URL, params=params, headers=headers, timeout=20)
            _S2_LAST_CALL[0] = time.time()
            last_status = r.status_code
            if r.status_code == 200:
                for p in r.json().get('data', []):
                    out.append({'title': p.get('title') or '', 'abstract': p.get('abstract') or '', 'year': p.get('year'), 'authors': [a.get('name') for a in (p.get('authors') or [])], 'url': p.get('url') or '', 'source': 'semantic_scholar'})
                _S2_FAIL_STREAK[0] = 0
                if stats is not None:
                    stats['s2_ok'] += 1
                    stats['s2_hits'] += len(out)
                    if attempt > 1:
                        stats['s2_recovered_after_retry'] += 1
                return out
            if r.status_code not in (429, 500, 502, 503, 504):
                print('  [warn] SemanticScholar status', r.status_code, 'for', query, '(not retried)')
                break
            ra = r.headers.get('Retry-After')
            if ra and str(ra).strip().isdigit():
                retry_after = int(ra)
        except Exception as e:
            last_status = type(e).__name__
        if attempt < S2_MAX_ATTEMPTS:
            delay = retry_after if retry_after is not None else 3 * (2 ** (attempt - 1))
            delay = min(60, delay) + random.uniform(0, 0.5)
            print('  [warn] SemanticScholar', last_status, 'for', query, '- retry', attempt, '/', S2_MAX_ATTEMPTS - 1, 'in', round(delay, 1), 's')
            time.sleep(delay)
    print('  [warn] SemanticScholar gave up (' + str(last_status) + ') for', query)
    _S2_FAIL_STREAK[0] += 1
    if stats is not None:
        stats['s2_failed'] += 1
    return out

EPMC_URL = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
OPENALEX_URL = 'https://api.openalex.org/works'
EXTRA_SOURCES_DEFAULT = 'europepmc,openalex'   # override with CORPUS_EXTRA_SOURCES=""  (empty = off) or e.g. "europepmc"


def _get_json_retry(url, params, name, stats, headers=None, attempts=3):
    """GET json with short retry on 429/5xx/exceptions. Returns parsed json or None (and counts failure)."""
    last = None
    for attempt in range(1, attempts + 1):
        try:
            r = requests.get(url, params=params, headers=headers or {}, timeout=25)
            last = r.status_code
            if r.status_code == 200:
                stats[name + '_ok'] += 1
                return r.json()
            if r.status_code not in (429, 500, 502, 503, 504):
                break
        except Exception as e:
            last = type(e).__name__
        if attempt < attempts:
            time.sleep(min(30, 3 * 2 ** (attempt - 1)) + random.uniform(0, 0.5))
    print('  [warn]', name, 'gave up (' + str(last) + ')')
    stats[name + '_failed'] += 1
    return None


def _strip_tags(text):
    return _clean_title(text)


def _search_europepmc(query, max_results=15, stats=None):
    out = []
    data = _get_json_retry(EPMC_URL, {'query': query, 'format': 'json', 'resultType': 'core', 'pageSize': max_results}, 'epmc', stats)
    for p in ((data or {}).get('resultList') or {}).get('result', []):
        title = _strip_tags(p.get('title'))
        if not title:
            continue
        pid, src = p.get('id'), p.get('source')
        url = ('https://europepmc.org/article/' + str(src) + '/' + str(pid)) if pid and src else ''
        authors = [a.strip() for a in (p.get('authorString') or '').rstrip('.').split(',') if a.strip()]
        out.append({'title': title, 'abstract': _strip_tags(p.get('abstractText')), 'year': p.get('pubYear'), 'authors': authors, 'url': url, 'source': 'europepmc', 'doi': _norm_doi(p.get('doi'))})
    if stats is not None:
        stats['epmc_hits'] += len(out)
    return out


def _openalex_abstract(inv):
    if not isinstance(inv, dict) or not inv:
        return ''
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return ' '.join(pos[i] for i in sorted(pos))


def _search_openalex(query, max_results=15, stats=None):
    out = []
    params = {'search': query, 'per-page': max_results,
              'select': 'id,doi,title,publication_year,authorships,abstract_inverted_index'}
    if os.getenv('OPENALEX_API_KEY'):
        params['api_key'] = os.getenv('OPENALEX_API_KEY')
    if os.getenv('OPENALEX_MAILTO'):
        params['mailto'] = os.getenv('OPENALEX_MAILTO')
    data = _get_json_retry(OPENALEX_URL, params, 'openalex', stats)
    for p in (data or {}).get('results', []):
        title = _strip_tags(p.get('title'))
        if not title:
            continue
        authors = [((a.get('author') or {}).get('display_name') or '') for a in (p.get('authorships') or [])]
        out.append({'title': title, 'abstract': _openalex_abstract(p.get('abstract_inverted_index')), 'year': p.get('publication_year'),
                    'authors': [a for a in authors if a], 'url': p.get('doi') or p.get('id') or '', 'source': 'openalex', 'doi': _norm_doi(p.get('doi'))})
    if stats is not None:
        stats['openalex_hits'] += len(out)
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

def _search_pubmed(query, max_results=15, stats=None):
    out = []
    try:
        params = {'db': 'pubmed', 'term': query, 'retmax': max_results, 'retmode': 'json'}
        r = requests.get(ES_URL, params=params, timeout=20)
        if r.status_code != 200:
            print('  [warn] PubMed esearch status', r.status_code, 'for', query)
            if stats is not None:
                stats['pubmed_failed'] += 1
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
            if stats is not None and not abstract:
                stats['pubmed_empty_abstracts'] += 1
            doi = ''
            for aid in (info.get('articleids') or []):
                if aid.get('idtype') == 'doi':
                    doi = _norm_doi(aid.get('value'))
            out.append({'title': title, 'doi': doi, 'abstract': abstract, 'year': (info.get('pubdate') or '')[:4], 'authors': [a.get('name') for a in info.get('authors', [])] if info.get('authors') else [], 'url': 'https://pubmed.ncbi.nlm.nih.gov/' + str(pmid) + '/', 'source': 'pubmed'})
            time.sleep(0.34)
    except Exception as e:
        print('  [warn] PubMed error:', e)
        if stats is not None:
            stats['pubmed_failed'] += 1
    return out

def build_corpus(topic_name, query_variants_file, max_per_query=15, verbose=True):
    queries = _load_queries(query_variants_file)
    if not queries:
        if verbose:
            print('  [warn] no queries in', query_variants_file)
        return []
    stats = {'queries': len(queries), 's2_ok': 0, 's2_failed': 0, 's2_skipped': 0, 'epmc_ok': 0, 'epmc_failed': 0, 'epmc_hits': 0, 'openalex_ok': 0, 'openalex_failed': 0, 'openalex_hits': 0, 's2_hits': 0, 's2_recovered_after_retry': 0,
             'pubmed_failed': 0, 'pubmed_empty_abstracts': 0, 'duplicates_merged': 0}
    _S2_FAIL_STREAK[0] = 0
    extra = [x.strip() for x in os.getenv('CORPUS_EXTRA_SOURCES', EXTRA_SOURCES_DEFAULT).split(',') if x.strip()]
    all_entries = []
    seen = {}          # normalised title -> entry
    seen_doi = {}      # normalised DOI -> entry (catches the same paper under differently written titles)
    for q in queries:
        if verbose:
            print('  -> querying:', q)
        # PubMed first so it stays the canonical record (full abstract) when other sources return the same paper.
        batches = [_search_pubmed(q, max_per_query, stats), _search_ss(q, max_per_query, stats)]
        if 'europepmc' in extra:
            batches.append(_search_europepmc(q, max_per_query, stats))
        if 'openalex' in extra:
            batches.append(_search_openalex(q, max_per_query, stats))
        for entry in [e for b in batches for e in b]:
            entry['title'] = _clean_title(entry['title'])
            k = _norm_title(entry['title'])
            if not k:
                continue
            doi = _norm_doi(entry.get('doi'))
            dup = _find_duplicate(k, seen)
            first = seen[dup] if dup is not None else (seen_doi.get(doi) if doi else None)
            if first is None:
                entry['sources'] = [entry['source']]
                seen[k] = entry
                if doi:
                    seen_doi[doi] = entry
                all_entries.append(entry)
            else:
                if doi and doi not in seen_doi:
                    seen_doi[doi] = first
                stats['duplicates_merged'] += 1
                if entry['source'] not in first['sources']:
                    first['sources'].append(entry['source'])
                if not (first.get('abstract') or '').strip() and (entry.get('abstract') or '').strip():
                    first['abstract'] = entry['abstract']
        time.sleep(0.5)
    stats['entries'] = len(all_entries)
    LAST_STATS.clear()
    LAST_STATS.update(stats)
    if verbose:
        print('  [' + topic_name + '] corpus built:', len(all_entries), 'unique entries')
        print('  [corpus stats] Semantic Scholar: ' + str(stats['s2_ok']) + '/' + str(stats['queries']) + ' queries ok ('
              + str(stats['s2_hits']) + ' hits, ' + str(stats['s2_recovered_after_retry']) + ' recovered by retry); PubMed: '
              + str(stats['queries'] - stats['pubmed_failed']) + '/' + str(stats['queries']) + ' queries ok, '
              + str(stats['pubmed_empty_abstracts']) + ' records without abstract; duplicates merged: ' + str(stats['duplicates_merged']))
        if extra:
            print('  [corpus stats] Europe PMC: ' + str(stats['epmc_ok']) + '/' + str(stats['queries']) + ' ok (' + str(stats['epmc_hits']) + ' hits); OpenAlex: '
                  + str(stats['openalex_ok']) + '/' + str(stats['queries']) + ' ok (' + str(stats['openalex_hits']) + ' hits)')
        _ok = [n for n, k in (('PubMed', stats['queries'] - stats['pubmed_failed']), ('Semantic Scholar', stats['s2_ok']), ('Europe PMC', stats['epmc_ok']), ('OpenAlex', stats['openalex_ok'])) if k > 0]
        print('  [corpus stats] sources that answered this run: ' + ', '.join(_ok))
        if stats['s2_ok'] == 0:
            print('  [WARN] Semantic Scholar returned nothing in this run - corpus relies on the other sources listed above.')
    return all_entries
