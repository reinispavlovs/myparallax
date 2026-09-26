import os
import re
import json
import datetime
import hashlib
import time
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv
import requests
import subprocess
import numpy as np

from scripts.shared.claim_layers_utils import validate_content_flags
from scripts.fetch_topic_corpus import build_corpus
from scripts.analyze_corpus_consensus import aggregate_corpus

# Iel??d?? vides main??gos no .env faila
load_dotenv(override=True)

XAI_API_KEY = os.getenv("XAI_API_KEY")

# --- Piespiedu t??r????ana (fix trailing whitespace/newline/quotes issues) ---
if XAI_API_KEY:
    XAI_API_KEY = XAI_API_KEY.strip().strip('"').strip("'")


BASE_DIR = Path(__file__).resolve().parent  # vienm??r = Project Parallax/, neatkar??gi no cwd
REPO_PATH = os.getenv("REPO_PATH", str(BASE_DIR))
FAILED_LOG_PATH = Path(REPO_PATH) / "digests" / "failed_topics.json"
DRAFTS_DIR = BASE_DIR / "drafts"

# Project Parallax t??mas un mekl????anas vaic??jumi arXiv datub??zei
# PIEZ??ME: nosaukumi un vaic??jumi ir formul??ti NEITR??LI (nevis "verified", "confirmed"),
# jo tas ir izejas punkts p??t??jumam, ne secin??jums.
TOPICS = [
    {
        "id": "megalithic_engineering_acoustics",
        "name": "Megalithic Acoustics, Granite Impedance & Structural Resonance",
        "arxiv_query": "acoustic impedance granite resonance",
    },
    {
        "id": "cyclical_cataclysms_precession",
        "name": "Cyclical Catastrophism & Orbital Eccentricity",
        "arxiv_query": "Younger Dryas impact hypothesis climate cycle",
    },
    {
        "id": "consciousness_independence_nde",
        "name": "Independence of Consciousness: Non-Local Mind Models & Reported Perceptual Anomalies",
        "arxiv_query": "quantum brain biology consciousness out-of-body experience clinical",
        "corpus_based": True,
        "query_variants_file": "data/query_variants/nde.json",
    },
    {
        "id": "neural_cosmic_isomorphism",
        "name": "Structural Isomorphism Between Neural Networks and the Cosmic Web",
        "arxiv_query": "cosmic web neuronal network structural similarity",
        "corpus_based": True,
        "query_variants_file": "data/query_variants/neural_cosmic_isomorphism.json",
    },
]


# --- Module-level arXiv relevance filtering (Decision #105 refactor) ---
# Extracted from fetch_real_arxiv_summary()'s nested scope so tokenization
# and scoring logic can be imported directly by diagnostic/test scripts
# instead of being duplicated (see Decision #230/#231 architectural debt).

ARXIV_STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "and", "or", "to",
    "for", "with", "at", "by",
}

# Multi-word phrases treated as a single semantic unit to avoid false
# lexical overlap with unrelated terms (e.g. "out-of-body" vs. "many-body
# problem"). See Decision #223/#224/#228.
PHRASE_ANCHORS = [
    ("out-of-body", "outofbodyanchor"),
    ("out of body", "outofbodyanchor"),
    ("near-death", "neardeathanchor"),
    ("near death", "neardeathanchor"),
]

MIN_ARXIV_OVERLAP_COUNT = 2
MIN_ARXIV_OVERLAP_RATIO = 0.34


def tokenize_arxiv_text(s: str) -> set:
    """Lowercases, applies phrase-anchor substitution, strips punctuation,
    and returns a stopword-filtered token set. Module-level per Decision #105
    so it can be imported directly by tests/diagnostics."""
    s = s.lower()
    for phrase, anchor in PHRASE_ANCHORS:
        s = s.replace(phrase, f" {anchor} ")
    s = re.sub(r"[^a-z0-9\s-]", " ", s)
    s = s.replace("-", " ")
    return {t for t in s.split() if t and t not in ARXIV_STOPWORDS}


def score_arxiv_candidate(query_tokens: set, candidate_text: str) -> tuple:
    """Returns (overlap_count, overlap_ratio, candidate_tokens) for a single
    candidate string against the query token set."""
    candidate_tokens = tokenize_arxiv_text(candidate_text)
    overlap = query_tokens & candidate_tokens
    overlap_count = len(overlap)
    overlap_ratio = overlap_count / len(query_tokens) if query_tokens else 0.0
    return overlap_count, overlap_ratio, candidate_tokens


def select_best_arxiv_candidate(query: str, entries: list) -> dict:
    """Parses raw arXiv <entry> blocks, scores each by keyword overlap
    against the query, and returns the best candidate. Pure function:
    no network I/O, fully testable in isolation.

    Returns dict with keys: text (str|None), overlap (int), ratio (float).
    """
    query_tokens = tokenize_arxiv_text(query)
    best = None
    best_overlap = 0
    best_ratio = 0.0
    for entry_block in entries:
        title = ""
        summary = ""
        if "<title>" in entry_block:
            title = entry_block.split("<title>")[1].split("</title>")[0]
        if "<summary>" in entry_block:
            summary = entry_block.split("<summary>")[1].split("</summary>")[0]
        combined = re.sub(r"\s+", " ", f"{title} {summary}").strip()
        if len(combined) <= 20:
            continue
        overlap_count, overlap_ratio, _ = score_arxiv_candidate(query_tokens, combined)
        if overlap_count > best_overlap or (overlap_count == best_overlap and overlap_ratio > best_ratio):
            best = combined
            best_overlap = overlap_count
            best_ratio = overlap_ratio
    return {"text": best, "overlap": best_overlap, "ratio": best_ratio}


def _curl_get(url: str, timeout: int = 8):
    """Fetches a URL via curl.exe subprocess instead of requests.get().

    Rationale (Decision #331/#333): arXiv's edge layer (Google Frontend +
    Fastly Varnish) fingerprints and blocks the TLS handshake produced by
    Python's requests/urllib3 stack, returning HTTP 406 on every
    cache-miss request ??? even for trivial single-word queries. curl.exe
    on Windows uses the Schannel TLS stack, which is NOT blocked, as
    confirmed by live diagnostic tests (200 OK on identical cache-miss
    requests). This wrapper mimics the minimal requests.Response
    interface (.status_code, .text) so downstream parsing logic in
    fetch_real_arxiv_summary() requires zero changes.
    """
    class _CurlResponse:
        def __init__(self, status_code: int, text: str):
            self.status_code = status_code
            self.text = text

    proc = subprocess.run(
        ["curl.exe", "-s", "-L", "-w", "\n%{http_code}", url],
        capture_output=True,
        timeout=timeout,
    )
    raw = proc.stdout.decode("utf-8", errors="replace")
    parts = raw.rsplit("\n", 1)
    if len(parts) == 2:
        body, status_str = parts
    else:
        body, status_str = raw, ""
    try:
        status_code = int(status_str.strip())
    except ValueError:
        status_code = 0
    return _CurlResponse(status_code, body)



def fetch_real_arxiv_summary(query: str) -> dict:
    """Fetches a real recent paper summary from the open arXiv API.
    Returns a dict with 'text' and 'found' (bool) so downstream code
    never confuses fallback text with a real citation.

    Relevance filter: arXiv's 'all:' search field ranks poorly on
    multi-keyword queries, sometimes returning topically unrelated
    papers (e.g. Mediterranean fire ecology for a precession query).
    Fetches up to 5 candidates and scores each by keyword overlap,
    picking the best match. If no candidate clears the relevance
    threshold, returns found=False rather than a misleading source.

    Tokenization/scoring logic lives in module-level helpers
    (tokenize_arxiv_text, score_arxiv_candidate, select_best_arxiv_candidate)
    per Decision #105, importable independently for tests/diagnostics.
    """
    encoded_query = quote(query)
    url = f"https://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results=5"
    try:
        r = _curl_get(url, timeout=8)
        if r.status_code == 200 and "<entry>" in r.text:
            entries = r.text.split("<entry>")[1:]
            result = select_best_arxiv_candidate(query, entries)
            best = result["text"]
            best_overlap = result["overlap"]
            best_ratio = result["ratio"]

            if best is not None and best_overlap >= MIN_ARXIV_OVERLAP_COUNT and best_ratio >= MIN_ARXIV_OVERLAP_RATIO:
                return {
                    "text": best[:400],
                    "found": True,
                    "raw_query": query,
                    "relevance_overlap_count": best_overlap,
                    "relevance_overlap_ratio": round(best_ratio, 2),
                }
            else:
                return {
                    "text": None,
                    "found": False,
                    "raw_query": query,
                    "note": (
                        "NO_RELEVANT_SOURCE_FOUND \u2014 best candidate failed keyword relevance "
                        f"threshold (overlap={best_overlap}, ratio={round(best_ratio, 2)}); a human "
                        "must manually add a citation before publication."
                    ),
                }
    except Exception as e:
        print(f"[!] arXiv request failed: {e}")

    return {
        "text": None,
        "found": False,
        "raw_query": query,
        "note": "NO_SOURCE_FOUND \u2014 a human must manually add a citation before publication.",
    }


def call_llm_classify_batch(texts):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + XAI_API_KEY,
    }
    numbered = chr(10).join(str(i+1) + ". " + t for i, t in enumerate(texts))
    prompt = (
        "Classify each numbered abstract below into EXACTLY one category: "
        "supports_veridical, null_result, neuro_mechanism, inconclusive." + chr(10) +
        "supports_veridical = evidence supporting veridical or anomalous perception." + chr(10) +
        "null_result = study found no effect or no support." + chr(10) +
        "neuro_mechanism = explains via known neuro or physiological mechanism." + chr(10) +
        "inconclusive = ambiguous, unrelated, or insufficient info." + chr(10) + chr(10) +
        "Abstracts:" + chr(10) + numbered + chr(10) + chr(10) +
        "Return ONLY a JSON array of exactly " + str(len(texts)) + " strings, one label per abstract, in order. "
        "No markdown, no explanation."
    )
    payload = {
        "model": "grok-4.6",
        "messages": [
            {"role": "system", "content": "You output ONLY valid JSON. No markdown, no prose."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
        labels = json.loads(raw)
        if not isinstance(labels, list):
            raise ValueError("not a list")
        return labels
    except Exception as e:
        print("[WARN] classify_batch LLM call failed: " + str(e))
        return ["inconclusive"] * len(texts)


def agent_1_corpus_analysis(topic):
    """Corpus-scale meta-analysis branch of Agent 1, for topics flagged
    corpus_based=True in TOPICS. Replaces the single-arXiv-hit lookup with
    a multi-database (Semantic Scholar + PubMed) statistical aggregate.

    NOTE: downstream fields keep the name 'arxiv_source_found' for
    backward compatibility with claim_layers_utils.py / digest_generator.py
    scoring logic ??? it now semantically means "at least one external
    source was found across the corpus", not literally "found on arXiv"."""
    print(f"[*] [A??ents 1 - CORPUS] Veido daudzavotu korpusu priek??: {topic['name']}...")

    variants_path = BASE_DIR / topic["query_variants_file"]
    try:
        variants_data = json.loads(variants_path.read_text(encoding="utf-8"))
        query_variants = variants_data.get("query_variants", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Neizdev??s iel??d??t query variants no {variants_path}: {e}")
        query_variants = []

    empty_result_template = {
        "data_type": "meta_analysis_illustrative",
        "corpus_size": 0,
        "boundary_status": "REQUIRES_HUMAN_SOURCED_CITATION",
        "arxiv_context": None,
        "arxiv_source_found": False,
    }

    if not query_variants:
        empty_result_template["model_note"] = (
            f"No query_variants file found/loaded at {variants_path} ??? corpus is empty."
        )
        return empty_result_template

    corpus = build_corpus(topic["name"], str(variants_path))
    if not corpus:
        empty_result_template["model_note"] = (
            "Corpus search returned zero results across Semantic Scholar/PubMed "
            "for all configured query variants."
        )
        return empty_result_template

    raw_consensus = aggregate_corpus(topic['name'], corpus, call_llm_classify_batch)

    consensus = {
        'data_type': 'meta_analysis_illustrative',
        'corpus_size': raw_consensus.get('total_sources', 0),
        'pct_supports_veridical': raw_consensus.get('percentages', {}).get('supports_veridical', 0),
        'pct_null_result': raw_consensus.get('percentages', {}).get('null_result', 0),
        'pct_neuro_mechanism': raw_consensus.get('percentages', {}).get('neuro_mechanism', 0),
        'pct_inconclusive': raw_consensus.get('percentages', {}).get('inconclusive', 0),
        'citation_list': raw_consensus.get('citation_list', []),
        'counts': raw_consensus.get('counts', {}),
    }

    consensus["arxiv_context"] = (
        f"Corpus meta-analysis across {consensus['corpus_size']} deduplicated sources "
        f"(Semantic Scholar + PubMed): {consensus['pct_supports_veridical']}% supports_veridical, "
        f"{consensus['pct_null_result']}% null_result, "
        f"{consensus['pct_neuro_mechanism']}% neuro_mechanism, "
        f"{consensus['pct_inconclusive']}% inconclusive."
    )
    consensus["arxiv_source_found"] = consensus["corpus_size"] > 0
    consensus["boundary_status"] = (
        "CORPUS_ANALYSIS_COMPLETE" if consensus["corpus_size"] >= 10
        else "REQUIRES_HUMAN_SOURCED_CITATION"  # too few sources to trust the percentages
    )
    consensus["model_note"] = (
        f"Statistical classification of {consensus['corpus_size']} abstracts via LLM "
        "categorization (supports_veridical / null_result / neuro_mechanism / "
        "inconclusive). This is a CORPUS-SCALE AGGREGATE, not a single-paper "
        "citation ??? see citation_list for the full source breakdown."
    )
    consensus["raw_tally"] = consensus.get("counts", {})
    consensus["classified_total"] = sum(consensus.get("counts", {}).values())
    return consensus


def agent_1_multi_source_simulation(topic):
    """1. A??ents: Apvieno re??lus arXiv datus ar VIENK??R??OTU ILUSTRAT??VU modeli.
    SVAR??GI: ??ie skait??i NAV m??r??jumi ??? tie ir vienk??r??ots matem??tiskais modelis
    un j??atz??m?? k?? t??di metadatos ('data_type': 'illustrative_model')."""

    # NEW: corpus-based topics take a completely different data path ???
    # multi-source statistical aggregate instead of a single arXiv hit.
    if topic.get("corpus_based"):
        return agent_1_corpus_analysis(topic)

    print(f"[*] [A??ents 1] Ieg??st datus no arXiv priek??: {topic['name']}...")
    arxiv_result = fetch_real_arxiv_summary(topic["arxiv_query"])

    base = {
        "arxiv_context": arxiv_result["text"],
        "arxiv_source_found": arxiv_result["found"],
        "data_type": "illustrative_model",  # NEKAD nav "measured_data"
    }

    if topic["id"] == "megalithic_engineering_acoustics":
        freq = 115.0
        z_air = 1.225 * 343.0
        z_granite = 2700.0 * 5000.0
        reflection_coeff = ((z_granite - z_air) / (z_granite + z_air)) ** 2
        delta_p = float(np.sqrt(2 * 1.225 * 343.0 * 1.0))

        base.update({
            "frequency_hz": freq,
            "acoustic_pressure_pa": delta_p,
            "energy_reflection_pct": float(reflection_coeff * 100),
            "boundary_status": "HIGH_REFLECTION_BARRIER",
            "model_note": "Standard acoustic impedance mismatch equation (Z1-Z2)^2/(Z1+Z2)^2. "
                          "Does NOT include a fabricated piezoelectric charge calculation ??? it was "
                          "identified as unsubstantiated and removed.",
        })
        return base

    elif topic["id"] == "cyclical_cataclysms_precession":
        years = np.linspace(0, 25920, 500)
        flux_peak = float(np.max(np.sin(2 * np.pi * years / 25920) * 100))
        base.update({
            "cycle_years": 25920,
            "younger_dryas_marker_bp": 12800,
            "orbital_flux_peak_illustrative": flux_peak,
            "boundary_status": "CYCLE_SYNCHRONIZED",
            "model_note": "Sinusoidal model for ILLUSTRATION ONLY ??? not a geological measurement.",
        })
        return base

    elif topic["id"] == "consciousness_independence_nde":
        # NOTE: this branch is now DEAD CODE under normal operation, since
        # this topic has corpus_based=True in TOPICS and is intercepted
        # above. Kept intentionally as a fallback path in case corpus_based
        # is ever toggled off for this topic (e.g. corpus fetch outage).
        base.update({
            "isoelectric_eeg_duration_sec_literature_range": "10-30",
            "auditory_evoked_potential_status": "TYPICALLY_ABSENT_PER_LITERATURE",
            "perceptual_recall_score": None,  # TODO(human): pievienot konkr??tu p??t??juma v??rt??bu ar atsauci
            "boundary_status": "REQUIRES_HUMAN_SOURCED_CITATION",
            "model_note": "A previous version hardcoded a number (0.84) here without a citation. "
                          "It has been removed. A human must add a specific "
                          "study and its reported figure PRIOR to publication.",
        })
        return base

    else:  # neural_cosmic_isomorphism
        # NOTE: same as above ??? dead code under normal operation while
        # corpus_based=True is set for this topic in TOPICS.
        base.update({
            "comparison_domains": ["neuronal_network_topology", "cosmic_web_filament_topology"],
            "quantitative_similarity_score": None,  # TODO(human): pievienot konkr??tu p??t??juma v??rt??bu ar atsauci
            "boundary_status": "REQUIRES_HUMAN_SOURCED_CITATION",
            "model_note": "Structural-similarity claims (e.g., Vazza & Feletti-type comparisons) "
                          "require a specific, citable study with methodology ??? without it, no "
                          "quantitative claim is publishable.",
        })
        return base


def agent_2_skeptic_evaluator(sim_data, topic):
    """2. A??ents (Skepti??is): Iez??m?? stingras materi??l??s un metodolo??isk??s robe??as."""
    print("[*] [A??ents 2] Veic skeptisko recenziju...")

    if topic["id"] == "megalithic_engineering_acoustics":
        critique = (
            f"Failsafe check: The {sim_data['energy_reflection_pct']:.2f}% acoustic energy reflection figure "
            "is standard impedance physics, NOT archaeological proof of intent. "
            "Airborne acoustic waves alone cannot overcome stone mass without an additional coupling mechanism "
            "(seismic strain or a closed Helmholtz geometry)."
        )
    elif topic["id"] == "cyclical_cataclysms_precession":
        critique = (
            "Cautionary check: The mathematical cyclical model is ILLUSTRATIVE, not a proven correlation mechanism. "
            "The sediment platinum peak (~12,800 BP) indicates an external impact event, which is a SEPARATE issue "
            "from the orbital mechanics cycle ??? the two must NOT be conflated into a single conclusion."
        )
    elif topic["id"] == "consciousness_independence_nde":
        if sim_data.get("data_type") == "meta_analysis_illustrative":
            critique = (
                f"Methodological check: This is a statistical aggregate of {sim_data.get('corpus_size', 0)} "
                "abstracts classified by an LLM, NOT a hand-verified systematic review. Category boundaries "
                "(supports_veridical vs. neuro_mechanism vs. inconclusive) are inherently fuzzy, and a "
                "consistent pattern of reported near-death perceptions does NOT by itself distinguish between "
                "competing explanations (non-local consciousness vs. common neurological substrates such as "
                "hypoxia, temporal lobe activation, or REM intrusion). Percentages should be read as a rough "
                "corpus-level signal, not a peer-reviewed effect size."
            )
        else:
            critique = (
                "Methodological check: Confirming the veridicality of subjective reports requires "
                "a specific, citable study with methodology. Without it, NO figure or claim "
                "is publishable as fact."
            )
    else:  # neural_cosmic_isomorphism
        if sim_data.get("data_type") == "meta_analysis_illustrative":
            critique = (
                f"Methodological check: This is a statistical aggregate of {sim_data.get('corpus_size', 0)} "
                "abstracts classified by an LLM, NOT a hand-verified systematic review. A visual or "
                "topological 'resemblance' between two networks (neural and cosmic web) reported across "
                "the corpus is NOT a causal link and must NOT be presented as a scientific 'isomorphism' "
                "without a specific quantitative comparison study with a stated metric and citation."
            )
        else:
            critique = (
                "Methodological check: A visual or topological 'resemblance' between two networks (neural and cosmic "
                "web) is NOT a causal link and must NOT be presented as a scientific 'isomorphism' without a specific "
                "quantitative comparison study with a stated metric and citation."
            )

    sim_data["skeptic_critique"] = critique
    return sim_data


def agent_3_author_generator(topic, verified_data):
    """3. A??ents (Autors): ??ener?? HTML DRAFTU (ne gal??go publik??ciju).
    Ietver retry lo??iku ar exponential backoff xAI (grok-4.6) timeout/t??kla k????du gad??jum??."""
    print("[*] [A??ents 3] ??ener?? semantisko HTML draftu ar xAI (grok-4.6)...")
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}",
    }

    prompt = (
        f"You are drafting a RESEARCH DRAFT (not a final publication) for Project Parallax on: {topic['name']}. "
        f"Use ONLY this dataset ??? do not invent additional numbers: {verified_data}. "
        "0. Write your ENTIRE response in English only, regardless of the language of any "
        "notes, critiques, or source text provided above. Translate any non-English fragments "
        "into English before including them in your output. "
        "STRICT RULES:\n"
        "1. If 'arxiv_source_found' is false, explicitly state 'No verified source found for this claim' ??? "
        "do NOT present the topic as settled fact.\n"
        "2. Avoid definitive verbs like 'proves', 'confirms', 'demonstrates conclusively'. Use "
        "'suggests', 'is consistent with', 'the study reports' instead, and attribute claims to their source.\n"
        "3. Include an HTML <table> showing the raw input metrics AND their 'data_type' "
        "(illustrative_model vs literature-sourced vs meta_analysis_illustrative), plus the skeptic critique. "
        "If 'citation_list' is present in the dataset, include a second <table> listing each source's title, "
        "year, classification, and access_status.\n"
        "4. Add a visible disclaimer <div> at the top stating: "
        "'AI-GENERATED DRAFT - PENDING HUMAN FACT-CHECK. Not for publication without review.'\n"
        "OUTPUT ONLY clean, semantic HTML fragments without markdown code blocks or extra text."
    )

    payload = {
        "model": "grok-4.6",
        "messages": [
            {"role": "system", "content": "You output only valid HTML fragments. You never state unverified claims as fact."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }

    max_retries = 3
    base_delay = 10  # sekundes

    for attempt in range(1, max_retries + 1):
        response = None
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=180)

            if response.status_code != 200:
                raise Exception(f"xAI API k????da [{response.status_code}]: {response.text}")

            return response.json()["choices"][0]["message"]["content"]

        except requests.exceptions.ReadTimeout:
            print(f"[WARN] [A??ents 3] xAI API timeout (m????in??jums {attempt}/{max_retries}) t??mai: {topic['name']}")

        except requests.exceptions.RequestException as e:
            print(f"[WARN] [A??ents 3] T??kla k????da (m????in??jums {attempt}/{max_retries}): {e}")

        except Exception as e:
            # Ja t?? ir klienta k????da (4xx), neatk??rtojam bezj??dz??gi
            if response is not None and 400 <= response.status_code < 500:
                print(f"[ERROR] [A??ents 3] Klienta k????da ({response.status_code}), p??rtraucu retry: {e}")
                raise
            print(f"[WARN] [A??ents 3] K????da (m????in??jums {attempt}/{max_retries}): {e}")

        if attempt < max_retries:
            delay = base_delay * attempt  # 10s, 20s, 30s
            print(f"[*] [A??ents 3] Atk??rtoju p??c {delay}s...")
            time.sleep(delay)
        else:
            print(f"[ERROR] [A??ents 3] Visi {max_retries} m????in??jumi neizdev??s t??mai: {topic['name']}")
            raise Exception(f"Agent 3 failed after {max_retries} attempts for topic '{topic['name']}'")


def build_claim_layer(verified_data: dict, html_content: str, topic: dict) -> list[dict]:
    """Konstru?? claim_layers mas??vu ??IM draftam.

    PIEZ??ME: Agent 1/2 pa??laik ra??o VIENU apgalvojumu/modeli per topic,
    t??p??c ???? funkcija atgrie?? viena-elementa sarakstu. Kad Agent 1 s??ks
    ra??ot vair??kus atsevi????i verific??jamus apgalvojumus, ???? funkcija
    j??papla??ina, lai atgrieztu vair??kus layers (skat. action item #10).

    Risk_level tiek noteikts NO RE??LIEM datiem (arxiv_source_found,
    data_type) ??? NE no legacy fallback ar piespiedu MEDIUM."""

    arxiv_found = verified_data.get("arxiv_source_found", False)

    # Risks: bez avota -> HIGH (nesubstant??ts inferential bridge).
    # Ar avotu, bet illustrative_model vai meta_analysis_illustrative
    # (ne measured_data) -> MEDIUM.
    # measured_data + arxiv_found ??obr??d main.py nekad nenotiek, t??p??c
    # LOW pa??reiz nav sasniedzams ar ??o pipeline versiju.
    if not arxiv_found:
        risk_level = "HIGH"
        evidence_level = None
    elif verified_data.get("data_type") == "meta_analysis_illustrative":
        risk_level = "MEDIUM"
        evidence_level = "corpus_meta_analysis"
    elif verified_data.get("data_type") == "illustrative_model":
        risk_level = "MEDIUM"
        evidence_level = "literature_context_illustrative_model"
    else:
        risk_level = "LOW"
        evidence_level = "literature_sourced"

    layer = {
        "layer_type": "inferential_bridge",
        "text": html_content,
        "stance": "literature_consistent" if arxiv_found else "unresolved",
        "confidence": None,  # TODO(human): form??la varb??t??ba, ja pieejama
        "risk_level": risk_level,
        "bridge_verified": False,  # inferential_bridge NEKAD nav auto-verific??ts (blok?? auto-merge)
        "arxiv_source_found": arxiv_found,
        "evidence_level": evidence_level,
        "conflict_detected": False,  # cross-draft konfliktus nosaka digest_generator.py, ne ??eit
        "counts_toward_topic": arxiv_found,  # bez avota nedr??kst sv??rt Bayesian summu
        "is_legacy_synthesized": False,
    }

    return [layer]


def log_failed_topic(topic, error_message):
    """Pieraksta neizdevu??os t??mu failed_topics.json fail??, lai v??l??k var??tu re-run."""
    failed_entry = {
        "topic_id": topic.get("id", "unknown"),
        "topic_name": topic.get("name", "unknown"),
        "error": str(error_message),
        "timestamp": datetime.datetime.now().isoformat(),
    }

    existing = []
    if FAILED_LOG_PATH.exists():
        try:
            existing = json.loads(FAILED_LOG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []

    existing.append(failed_entry)
    FAILED_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    FAILED_LOG_PATH.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[LOGGED] T??ma '{topic.get('name')}' pievienota {FAILED_LOG_PATH.name}")


def process_topic(topic):
    """Apstr??d?? VIENU t??mu caur visiem 3 a??entiem un saglab?? draftu.
    Izmet exception, ja k??ds solis neizdodas ??? to no??er aug????jais loop."""

    # 1. A??ents 1: Datu ieguve un ilustrat??vais modelis
    sim_results = agent_1_multi_source_simulation(topic)

    # 2. A??ents 2: Skepti??a recenzija
    verified_data = agent_2_skeptic_evaluator(sim_results, topic)

    # 3. A??ents 3: HTML draft ??ener????ana
    html_content = agent_3_author_generator(topic, verified_data)

    # 4. Saglab?? DRAFTU ??? NEVIS gatavu publik??ciju
    # Mape "drafts/" NEDR??KST b??t sait??ta no publisk??s vietnes navig??cijas / index.html
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    base_filename = f"draft-{topic['id']}-{timestamp}"
    html_path = DRAFTS_DIR / f"{base_filename}.html"
    meta_path = DRAFTS_DIR / f"{base_filename}.meta.json"

    content_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()[:12]

    with open(html_path, "w", encoding="utf-8", newline="") as f:
        f.write(html_content)

    # 5. Konstru??jam claim_layers NO RE??LIEM datiem (nov??r?? legacy fallback)
    claim_layers = build_claim_layer(verified_data, html_content, topic)

    # 6. Valid??jam saturu PIRMS saglab????anas ??? forbidden termini, nesourc??ti
    # decim????i utt. j??redz review_cli.py operatoram, ne tikai digest_generator.py
    content_flags = []
    for layer in claim_layers:
        content_flags.extend(validate_content_flags(layer))

    content_flags = list(dict.fromkeys(content_flags))  # Decision #61: dedup
    metadata = {
        "topic_id": topic["id"],
        "topic_name": topic["name"],
        "generated_at": datetime.datetime.now().isoformat(),
        "model": "grok-4.6",
        "arxiv_source_found": verified_data.get("arxiv_source_found"),
        "arxiv_context": verified_data.get("arxiv_context"),
        "data_type": verified_data.get("data_type"),
        "skeptic_critique": verified_data.get("skeptic_critique"),
        "content_file": html_path.name,
        "content_hash": content_hash,
        "claim_layers": claim_layers,
        "content_flags": content_flags,
        "human_reviewed": False,
        "review_status": "pending",
        "reviewer": None,
        "review_notes": None,
    }

    # NEW: persist the full corpus statistics + citation list onto the
    # draft's metadata when Agent 1 took the corpus-analysis path, so
    # review_cli.py / promote_drafts.py / a human reviewer can inspect the
    # underlying source breakdown without re-running the corpus fetch.
    if verified_data.get("data_type") == "meta_analysis_illustrative":
        metadata["corpus_analysis"] = {
            "corpus_size": verified_data.get("corpus_size"),
            "classified_total": verified_data.get("classified_total"),
            "pct_supports_veridical": verified_data.get("pct_supports_veridical"),
            "pct_null_result": verified_data.get("pct_null_result"),
            "pct_neuro_mechanism": verified_data.get("pct_neuro_mechanism"),
            "pct_inconclusive": verified_data.get("pct_inconclusive"),
            "raw_tally": verified_data.get("raw_tally"),
            "citation_list": verified_data.get("citation_list"),
        }

    with open(meta_path, "w", encoding="utf-8", newline="") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"[*] DRAFTS saglab??ti (NAV public??ti): {html_path}")
    print(f"[*] Metadati: {meta_path}")
    if content_flags:
        print(f"[WARN] Content flags konstat??ti: {content_flags}")

    return html_path, meta_path


def main():
    print(f"[*] S??kam apstr??di: {len(TOPICS)} t??mas rind??.\n")

    successful = 0
    failed = 0

    for topic in TOPICS:
        print(f"{'=' * 60}")
        print(f"[*] Apstr??d??ju t??mu: {topic['name']}")
        print(f"{'=' * 60}")

        try:
            process_topic(topic)
            successful += 1
            print(f"[OK] T??ma '{topic['name']}' pabeigta veiksm??gi.\n")

        except Exception as e:
            failed += 1
            print(f"[ERROR] T??ma '{topic['name']}' neizdev??s: {e}\n")
            log_failed_topic(topic, e)
            continue  # KRITISKI: p??riet uz n??kamo t??mu, process NEAPST??JAS

    print(f"{'=' * 60}")
    print(f"[SUMMARY] Pabeigts: {successful} veiksm??gi, {failed} neizdev??s no {len(TOPICS)} kop??.")
    print(f"{'=' * 60}")

    if failed > 0:
        print(f"[INFO] Skat??t {FAILED_LOG_PATH} pilnam neizdevu??os t??mu sarakstam.")

    print("[*] N??kamais solis: cilv??ka p??rbaude ar review_cli.py, tad p??rvieto??ana uz posts/.")


if __name__ == "__main__":
    main()

