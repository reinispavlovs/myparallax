import time

VALID_CATEGORIES = ['supports_veridical', 'null_result', 'neuro_mechanism', 'inconclusive']

def _truncate(text, limit=500):
    if not text:
        return ''
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + '...'

def _prepare_batches(corpus_entries, batch_size=10):
    usable = [e for e in corpus_entries if e.get('abstract') or e.get('title')]
    batches = []
    for i in range(0, len(usable), batch_size):
        batches.append(usable[i:i+batch_size])
    return batches

def aggregate_corpus(topic_name, corpus_entries, classify_fn, batch_size=10, verbose=True):
    if not corpus_entries:
        return {'topic': topic_name, 'total_sources': 0, 'counts': {c: 0 for c in VALID_CATEGORIES}, 'percentages': {c: 0.0 for c in VALID_CATEGORIES}, 'citation_list': []}

    batches = _prepare_batches(corpus_entries, batch_size)
    counts = {c: 0 for c in VALID_CATEGORIES}
    citation_list = []
    classified_total = 0

    for bi, batch in enumerate(batches):
        texts = []
        for entry in batch:
            snippet = entry.get('abstract') or entry.get('title') or ''
            texts.append(_truncate(snippet, 500))

        if verbose:
            print('  [batch ' + str(bi+1) + '/' + str(len(batches)) + '] classifying ' + str(len(texts)) + ' abstracts...')

        try:
            labels = classify_fn(texts)
        except Exception as e:
            print('  [warn] classify_fn error on batch ' + str(bi+1) + ':', e)
            labels = ['inconclusive'] * len(texts)

        if len(labels) != len(texts):
            while len(labels) < len(texts):
                labels.append('inconclusive')
            labels = labels[:len(texts)]

        for entry, label in zip(batch, labels):
            label = label.strip().lower() if isinstance(label, str) else 'inconclusive'
            if label not in VALID_CATEGORIES:
                label = 'inconclusive'
            counts[label] += 1
            classified_total += 1
            citation_list.append({'title': entry.get('title', ''), 'year': entry.get('year'), 'authors': entry.get('authors', []), 'url': entry.get('url', ''), 'source': entry.get('source', ''), 'classification': label})

        time.sleep(0.2)

    percentages = {}
    for c in VALID_CATEGORIES:
        if classified_total > 0:
            percentages[c] = round((counts[c] / classified_total) * 100, 1)
        else:
            percentages[c] = 0.0

    if verbose:
        print('  [' + topic_name + '] classification complete: ' + str(classified_total) + ' sources')
        for c in VALID_CATEGORIES:
            print('    ' + c + ': ' + str(counts[c]) + ' (' + str(percentages[c]) + '%)')

    return {'topic': topic_name, 'total_sources': classified_total, 'counts': counts, 'percentages': percentages, 'citation_list': citation_list}
