import re
import time

VALID_CATEGORIES = ['supports_veridical', 'null_result', 'neuro_mechanism', 'observational_signal', 'inconclusive']


class ClassificationError(RuntimeError):
    """Classification could not be completed. Never converted to 'inconclusive' labels: the topic
    must fail (no draft, nothing for promote_drafts / the Tribunal to pick up)."""

# --- Relevance gate (tiered): classifies every entry, removes nothing unless enforced ---
# Curated per topic (keyed by the exact topic name main.py passes in). Verdict order:
#   Tier A  specific, low-collision terms (title or abstract)           -> relevant
#   Tier C  hard-exclude domain markers (checked on the TITLE only),
#           skipped when any Tier A term is present                      -> off-topic
#   Tier B  topical groups: ONE group in the title, or at least
#           b_abstract_min_groups DISTINCT groups across title+abstract  -> relevant
#   otherwise                                                           -> off-topic
# A group is {'any': [patterns], 'also': [patterns], 'also_all': [[patterns], ...]}:
# 'also' (optional) needs one match; every list inside 'also_all' (optional) needs one match.
# A Tier A term in the TITLE is unconditional; found only in the abstract it needs
# tier_a_abstract_min_matches occurrences (a single incidental mention is not enough).
# Abstracts are trimmed of PubMed record header/footer (citation, title, authors,
# affiliations, copyright, DOI/PMID, conflict statement) before any matching.
# Generic words (conscious, awareness, lucid, recall, dying, cardiac arrest, end-of-life)
# are deliberately NOT usable on their own.
# The gate runs on every entry, but removal happens AFTER classification and only for
# entries whose label is 'inconclusive': any informative label is protected (see
# PROTECTED_LABELS), so the gate can only shrink the inconclusive pool and never tilts
# support or counterweight in either direction.
# Exception: Tier C groups listed in a rule's 'tier_c_hard' (e.g. veterinary/livestock) are
# categorically not evidence about the topic, so they are flagged for removal whatever label the
# classifier gave them (reported as 'hard exclude'). Tier A/B hits still win over Tier C.
# ENFORCE_RELEVANCE = False -> shadow mode: report what WOULD be dropped, drop nothing.
# ENFORCE_RELEVANCE = True  -> flagged entries are dropped AFTER classification (rules above) and are
# listed with reason/label in the result ('excluded'), so published counts stay auditable.
ENFORCE_RELEVANCE = True
PROTECTED_LABELS = tuple(c for c in VALID_CATEGORIES if c != 'inconclusive')
RELEVANCE_RULES = {
    "Independence of Consciousness: Non-Local Mind Models & Reported Perceptual Anomalies": {
        "tier_a": [
            r"near[- ]death", r"\bndes?\b", r"\bobes?\b", r"out[- ]of[- ]body",
            r"terminal lucidity", r"paradoxical lucidity", r"end[- ]of[- ]life experiences?",
            r"death[- ]?bed", r"shared[- ]death", r"veridical", r"peri-?mortem",
            r"dying[- ]moment", r"dying (\w+ )?brains?",
            r"rem(-| sleep )?intrusions?",
            r"non-?local (consciousness|mind)", r"survival of (consciousness|the mind)",
            r"reducing valve", r"(filter|transmission) (theory|model|hypothesis) of (consciousness|mind|the brain)",
        ],
        "tier_b": {
            "death-boundary brain state": {
                "any": [r"between life and death", r"twilight zones?", r"moment of death",
                        r"process of dying", r"dying process"],
            },
            "no-flow / arrest consciousness": {
                "any": [r"circulatory arrest", r"cardiac arrest"],
                "also": [r"conscious", r"awareness", r"aware\b"],
            },
            "resuscitation consciousness": {
                "any": [r"resuscitation[- ]induced consciousness", r"cpr[- ]induced consciousness",
                        r"awareness (during|under) (cpr|resuscitation|cardiac arrest)",
                        r"consciousness during (cpr|resuscitation|cardiac arrest)",
                        r"signs of life"],
                "also": [r"cardiac arrest", r"\bcpr\b", r"resuscitat"],
                "also_all": [[r"experience", r"recall", r"memor(y|ies)", r"percept(ion|ions|ual)"]],
            },
            "experiential-content analysis": {
                "any": [r"\bdmt\b", r"psychedelic", r"psilocybin", r"5-meo", r"ayahuasca",
                        r"mystical", r"ego[- ]dissolution"],
                "also": [r"thematic (and content )?analysis", r"content analysis",
                         r"phenomenolog", r"mystical experience", r"encounter with"],
            },
        },
        "tier_a_abstract_min_matches": 2,
        "b_abstract_min_groups": 2,
        "tier_c_hard": ["veterinary/livestock"],
        "tier_c": {
            "veterinary/livestock": {
                "any": [r"\b(sheep|goats?|calves|calf|donkeys?|halibut|piglets?|dogs?|canine|bovine|porcine|ovine|equine|swine|ruminants?|livestock|poultry|leopard|slaughter|stunning)\b",
                        r"captive[- ]bolt", r"\bhalal\b", r"euthanasia (agent|of)"],
            },
            "basic biology/oncology/pharmacology": {
                "any": [r"transcriptom", r"cell death", r"\btumou?rs?\b", r"carcinoma|leukemia|lymphoma|metasta",
                        r"\bvaccines?\b", r"liposom", r"regenerat", r"proteoform|exome|genomic|single-cell|multi-omics",
                        r"progenitor|stem cells?", r"receptor (agonist|inhibit|antagonist)", r"channel inhibition",
                        r"tamoxifen|dentin|sphingolipid|fluorescent agent"],
            },
            "neurodegeneration/stroke/encephalitis": {
                "any": [r"alzheimer", r"parkinson", r"amyotrophic", r"multiple sclerosis", r"neurodegenerat",
                        r"encephalitis", r"ischemic stroke", r"intracerebral hemorrhage"],
            },
            "epidemiology/health systems": {
                "any": [r"registry|registration", r"\bseer\b", r"nationwide", r"cross-sectional",
                        r"competing[- ]risk", r"disparities", r"forecasts?", r"policy analysis",
                        r"knowledge, attitudes"],
            },
            "clinical case report (non-consciousness)": {
                "any": [r"case report", r"case series"],
                "also": [r"anaphyla", r"appendicitis", r"thoracotomy", r"embolism", r"liver", r"surg",
                         r"nursing", r"trauma", r"opportunistic", r"radiotherapy", r"cancer", r"hypothermia"],
            },
            "psychedelic clinical primer/risk": {
                "any": [r"\bprimer\b", r"suicidality"],
            },
            "accidental hypothermia": {
                "any": [r"accidental (environmental )?hypothermia"],
            },
            "anesthesia monitoring technology": {
                "any": [r"isoflurane", r"\bbis monitor", r"anesthetized"],
            },
        },
    },
}


def _first_match(patterns, text):
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return None


def _count_matches(patterns, text):
    hits = []
    for p in patterns:
        hits.extend(m.group(0) for m in re.finditer(p, text))
    return hits


def _group_match(group, text):
    hit = _first_match(group['any'], text)
    if hit is None:
        return None
    also = group.get('also')
    if also and _first_match(also, text) is None:
        return None
    for required in group.get('also_all') or []:
        if _first_match(required, text) is None:
            return None
    return hit


_PUBMED_FOOTER = re.compile(r'^(copyright\b|\u00a9|doi:|pmid:|pmcid:|conflict of interest|\[indexed for medline\]|'
                            r'comment in|erratum in|update of|republished|retraction)', re.I)


def _norm_ws(text):
    return re.sub(r'\s+', ' ', text or '').strip().lower()


def _looks_like_authors(block):
    tokens = re.findall(r"[A-Za-z][\w'\u2019-]*", block)
    if not tokens or len(block) > 400 or ',' not in block:
        return False
    capped = sum(1 for t in tokens if t[0].isupper())
    return capped / float(len(tokens)) >= 0.8


def _trim_pubmed_abstract(raw, title=''):
    """Strip PubMed text-record header/footer from an abstract. Unrecognised formats are returned unchanged."""
    text = (raw or '').strip()
    if not text:
        return ''
    blocks = [b.strip() for b in re.split(r'\n\s*\n', text) if b.strip()]
    start = 0
    for i, b in enumerate(blocks[:8]):
        if b.lower().startswith('author information'):
            start = i + 1
            break
    else:
        if blocks and re.match(r'^\d+\.\s', blocks[0]):
            start = 1
            t = _norm_ws(title)[:40]
            if start < len(blocks) and t and t in _norm_ws(blocks[start]):
                start += 1
            if start < len(blocks) and _looks_like_authors(blocks[start]):
                start += 1
    kept = []
    for b in blocks[start:]:
        if _PUBMED_FOOTER.match(b):
            break
        cut = re.search(r'(?:^|\s)(?:\u00a9|copyright\b)', b, re.I)
        if cut:
            head = b[:cut.start()].strip()
            if head:
                kept.append(head)
            break
        kept.append(b)
    trimmed = '\n\n'.join(kept).strip()
    if trimmed:
        return trimmed
    return '' if start > 0 else text  # header recognised but no abstract body -> empty, never the header


def _assess_relevance(entry, rule):
    title = (entry.get('title') or '').lower()
    abstract = _trim_pubmed_abstract(entry.get('abstract'), entry.get('title') or '').lower()
    text = (title + ' ' + abstract).strip()

    hit = _first_match(rule['tier_a'], title)
    if hit is not None:
        return {'relevant': True, 'tier': 'A', 'reason': "Tier A term in title '" + hit + "'"}
    need_a = rule.get('tier_a_abstract_min_matches', 2)
    abs_hits = _count_matches(rule['tier_a'], abstract)
    if len(abs_hits) >= need_a:
        return {'relevant': True, 'tier': 'A-abstract',
                'reason': 'Tier A terms in abstract only (' + str(len(abs_hits)) + ' matches, e.g. \'' + abs_hits[0] + '\')'}

    c_text = title or abstract
    for name, group in rule['tier_c'].items():
        hit = _group_match(group, c_text)
        if hit is not None:
            return {'relevant': False, 'tier': 'C',
                    'hard': name in rule.get('tier_c_hard', ()),
                    'reason': "Tier C exclude [" + name + "]: '" + hit + "' (no Tier A term)"}

    title_groups = [n for n, g in rule['tier_b'].items() if _group_match(g, title) is not None]
    if title_groups:
        return {'relevant': True, 'tier': 'B-title', 'reason': 'Tier B title group: ' + ', '.join(title_groups)}

    text_groups = [n for n, g in rule['tier_b'].items() if _group_match(g, text) is not None]
    need = rule.get('b_abstract_min_groups', 2)
    if len(text_groups) >= need:
        return {'relevant': True, 'tier': 'B-abstract', 'reason': 'Tier B text groups: ' + ', '.join(text_groups)}

    a_note = ('; ' + str(len(abs_hits)) + ' Tier A abstract mention(s), need ' + str(need_a)) if abs_hits else ''
    return {'relevant': False, 'tier': 'none',
            'reason': 'no Tier A term in title' + a_note + '; no Tier C hit; Tier B title groups: none; Tier B text groups: '
                      + (', '.join(text_groups) or 'none') + ' (need ' + str(need) + ')'}


def _assess_corpus(topic_name, entries, verbose=True):
    """Return {id(entry): verdict} for topics that have a rule, else {}. Removes nothing."""
    rule = RELEVANCE_RULES.get(topic_name)
    if not rule:
        return {}
    verdicts = {id(e): _assess_relevance(e, rule) for e in entries}
    if verbose:
        flagged = [e for e in entries if not verdicts[id(e)]['relevant']]
        mode = 'ENFORCED after classification (inconclusive only)' if ENFORCE_RELEVANCE else 'shadow mode - nothing removed'
        print('  [relevance] ' + str(len(flagged)) + '/' + str(len(entries)) + ' entries flagged off-topic (' + mode + ')')
        for e in flagged:
            v = verdicts[id(e)]
            print('    - ' + _truncate(e.get('title') or '(no title)', 110) + '  <- ' + v['reason'])
    return verdicts

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

def _classification_text(entry, limit=500):
    """Text sent to the classifier: title + abstract with the PubMed record header/footer removed,
    whitespace collapsed to single spaces (the prompt numbers one text per line)."""
    title = (entry.get('title') or '').strip()
    body = re.sub(r'\s+', ' ', _trim_pubmed_abstract(entry.get('abstract'), title)).strip()
    if not body:
        return _truncate(title, limit)
    return (title.rstrip('.') + '. ' if title else '') + _truncate(body, limit)

def aggregate_corpus(topic_name, corpus_entries, classify_fn, batch_size=10, verbose=True):
    if not corpus_entries:
        return {'topic': topic_name, 'total_sources': 0, 'counts': {c: 0 for c in VALID_CATEGORIES}, 'percentages': {c: 0.0 for c in VALID_CATEGORIES}, 'citation_list': [],
                'retrieved_total': 0, 'relevance_enforced': False, 'excluded_count': 0, 'excluded': []}

    relevance = _assess_corpus(topic_name, corpus_entries, verbose)
    relevance_removed = []
    relevance_protected = []
    relevance_hard = []
    excluded = []
    batches = _prepare_batches(corpus_entries, batch_size)
    counts = {c: 0 for c in VALID_CATEGORIES}
    citation_list = []
    classified_total = 0

    for bi, batch in enumerate(batches):
        texts = []
        for entry in batch:
            texts.append(_classification_text(entry, 500))

        if verbose:
            print('  [batch ' + str(bi+1) + '/' + str(len(batches)) + '] classifying ' + str(len(texts)) + ' abstracts...')

        try:
            labels = classify_fn(texts)
        except ClassificationError:
            raise
        except Exception as e:
            raise ClassificationError('classify_fn failed on batch ' + str(bi+1) + '/' + str(len(batches))
                                      + ' for topic ' + repr(topic_name) + ': ' + str(e)) from e

        if not isinstance(labels, (list, tuple)) or len(labels) != len(texts):
            got = len(labels) if isinstance(labels, (list, tuple)) else type(labels).__name__
            raise ClassificationError('classify_fn returned ' + str(got) + ' labels for ' + str(len(texts))
                                      + ' texts on batch ' + str(bi+1) + '/' + str(len(batches))
                                      + ' for topic ' + repr(topic_name))

        for entry, label in zip(batch, labels):
            label = label.strip().lower() if isinstance(label, str) else 'inconclusive'
            if label not in VALID_CATEGORIES:
                label = 'inconclusive'
            verdict = relevance.get(id(entry))
            if verdict is not None and not verdict['relevant']:
                if label in PROTECTED_LABELS and not verdict.get('hard'):
                    relevance_protected.append((entry.get('title') or '(no title)', label, verdict['reason']))
                else:
                    why = verdict['reason']
                    if label in PROTECTED_LABELS:
                        why = 'HARD EXCLUDE despite label ' + label + ' - ' + why
                        relevance_hard.append((entry.get('title') or '(no title)', label))
                    relevance_removed.append((entry.get('title') or '(no title)', why))
                    excluded.append({'title': entry.get('title', ''), 'year': entry.get('year'), 'url': entry.get('url', ''),
                                     'source': entry.get('source', ''), 'label': label, 'tier': verdict.get('tier'),
                                     'reason': verdict['reason']})
                    if ENFORCE_RELEVANCE:
                        continue
            counts[label] += 1
            classified_total += 1
            citation_list.append({'title': entry.get('title', ''), 'year': entry.get('year'), 'authors': entry.get('authors', []), 'url': entry.get('url', ''), 'source': entry.get('source', ''), 'classification': label})

        time.sleep(0.2)

    if verbose and relevance:
        verb = 'removed' if ENFORCE_RELEVANCE else 'would be removed'
        print('  [relevance] ' + str(len(relevance_removed)) + ' flagged entries ' + verb + ' ('
              + str(len(relevance_hard)) + ' hard-excluded despite an informative label); '
              + str(len(relevance_protected)) + ' flagged entries kept (informative label protected)')
        for t, lab in relevance_hard:
            print('    - HARD EXCLUDE [' + lab + '] ' + _truncate(t, 100))
        for t, lab, why in relevance_protected:
            print('    - PROTECTED [' + lab + '] ' + _truncate(t, 100) + '  <- ' + why)

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

    return {'topic': topic_name, 'total_sources': classified_total, 'counts': counts, 'percentages': percentages, 'citation_list': citation_list,
            'retrieved_total': len(corpus_entries), 'relevance_enforced': bool(ENFORCE_RELEVANCE and relevance),
            'excluded_count': len(excluded) if (ENFORCE_RELEVANCE and relevance) else 0, 'excluded': excluded}
