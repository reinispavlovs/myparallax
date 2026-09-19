import os
import re
import json
import datetime
import random
import hashlib
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv
import requests
import numpy as np

# Ielādē vides mainīgos no .env faila
load_dotenv()

XAI_API_KEY = os.getenv("XAI_API_KEY")
REPO_PATH = os.getenv("REPO_PATH", ".")

# Project Parallax tēmas un meklēšanas vaicājumi arXiv datubāzei
# PIEZĪME: nosaukumi un vaicājumi ir formulēti NEITRĀLI (nevis "verified", "confirmed"),
# jo tas ir izejas punkts pētījumam, ne secinājums.
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
    },
    {
        "id": "neural_cosmic_isomorphism",
        "name": "Structural Isomorphism Between Neural Networks and the Cosmic Web",
        "arxiv_query": "cosmic web neuronal network structural similarity",
    },
]


def fetch_real_arxiv_summary(query: str) -> dict:
    """Iegūst reālu jaunāko pētījumu kopsavilkumu no arXiv atvērtā API.
    Atgriež dict ar 'text' un 'found' (bool), lai lejup pa plūsmu NEKAD
    nesajauktu fallback tekstu ar reālu citātu."""
    encoded_query = quote(query)
    url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results=1"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200 and "<summary>" in r.text:
            summary = r.text.split("<summary>")[1].split("</summary>")[0].strip()
            summary = re.sub(r"\s+", " ", summary)
            if len(summary) > 20:
                return {"text": summary[:400], "found": True, "raw_query": query}
    except Exception as e:
        print(f"[!] arXiv pieprasījums neizdevās: {e}")

    return {
        "text": None,
        "found": False,
        "raw_query": query,
        "note": "NO_SOURCE_FOUND — cilvēkam manuāli jāpievieno atsauce pirms publicēšanas.",
    }


def agent_1_multi_source_simulation(topic):
    """1. Aģents: Apvieno reālus arXiv datus ar VIENKĀRŠOTU ILUSTRATĪVU modeli.
    SVARĪGI: šie skaitļi NAV mērījumi — tie ir vienkāršots matemātiskais modelis
    un jāatzīmē kā tādi metadatos ('data_type': 'illustrative_model')."""
    print(f"[*] [Aģents 1] Iegūst datus no arXiv priekš: {topic['name']}...")
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
            "model_note": "Standarta akustiskās impedances vienādojums (Z1-Z2)^2/(Z1+Z2)^2. "
                          "NAV iekļauts izgudrots pjezoelektriskā lādiņa aprēķins — tas tika "
                          "identificēts kā nepamatots un noņemts.",
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
            "model_note": "Sinusoidāls modelis TIKAI ilustrācijai — nav ģeoloģisks mērījums.",
        })
        return base

    elif topic["id"] == "consciousness_independence_nde":
        base.update({
            "isoelectric_eeg_duration_sec_literature_range": "10-30",
            "auditory_evoked_potential_status": "TYPICALLY_ABSENT_PER_LITERATURE",
            "perceptual_recall_score": None,  # TODO(human): pievienot konkrētu pētījuma vērtību ar atsauci
            "boundary_status": "REQUIRES_HUMAN_SOURCED_CITATION",
            "model_note": "Iepriekšējā versijā šeit bija hardkodēts skaitlis (0.84) bez atsauces. "
                          "Tas ir noņemts. Cilvēkam PIRMS publicēšanas jāpievieno konkrēts "
                          "pētījums un tā ziņotais rādītājs.",
        })
        return base

    else:  # neural_cosmic_isomorphism
        base.update({
            "comparison_domains": ["neuronal_network_topology", "cosmic_web_filament_topology"],
            "quantitative_similarity_score": None,  # TODO(human): pievienot konkrētu pētījuma vērtību ar atsauci
            "boundary_status": "REQUIRES_HUMAN_SOURCED_CITATION",
            "model_note": "Strukturālās līdzības apgalvojumi (piem., Vazza & Feletti tipa salīdzinājumi) "
                          "prasa konkrētu citējamu pētījumu ar metodoloģiju — bez tā nav publicējams "
                          "kvantitatīvs apgalvojums.",
        })
        return base


def agent_2_skeptic_evaluator(sim_data, topic):
    """2. Aģents (Skeptiķis): Iezīmē stingras materiālās un metodoloģiskās robežas."""
    print("[*] [Aģents 2] Veic skeptisko recenziju...")

    if topic["id"] == "megalithic_engineering_acoustics":
        critique = (
            f"Failsafe check: {sim_data['energy_reflection_pct']:.2f}% akustiskās energijas atstarošanās "
            "aprēķins ir standarta impedances fizika, NE arheoloģisks pierādījums par nodomu. "
            "Gaisa akustiskie viļņi vien nevar pārvarēt akmens masu bez papildu savienojuma mehānisma "
            "(seismiska sprieguma vai slēgtas Helmholtz ģeometrijas)."
        )
    elif topic["id"] == "cyclical_cataclysms_precession":
        critique = (
            "Cautionary check: Matemātiskais cikliskais modelis ir ILUSTRATĪVS, ne pierādīts korelācijas mehānisms. "
            "Nogulumu platīna pīķi (~12 800 BP) liecina par ārēju trieciena notikumu, kas ir ATSEVIŠĶS jautājums "
            "no orbitālās mehānikas cikla — šos divus NEDRĪKST sajaukt vienā secinājumā."
        )
    elif topic["id"] == "consciousness_independence_nde":
        critique = (
            "Methodological check: Subjektīvo ziņojumu patiesuma (veridicality) apstiprināšanai nepieciešams "
            "konkrēts, citējams pētījums ar metodoloģiju. Bez tā NEVIENS skaitlis vai apgalvojums "
            "NAV publicējams kā fakts."
        )
    else:  # neural_cosmic_isomorphism
        critique = (
            "Methodological check: Vizuāla vai topoloģiska 'līdzība' starp diviem tīkliem (neironu un kosmiskā "
            "tīkla) NAV cēloniska saikne un NEDRĪKST tikt prezentēta kā zinātnisks 'izomorfisms' bez konkrēta "
            "kvantitatīva salīdzinājuma pētījuma ar norādītu metriku un atsauci."
        )

    sim_data["skeptic_critique"] = critique
    return sim_data


def agent_3_author_generator(topic, verified_data):
    """3. Aģents (Autors): Ģenerē HTML DRAFTU (ne galīgo publikāciju)."""
    print("[*] [Aģents 3] Ģenerē semantisko HTML draftu ar xAI (grok-4.6)...")
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}",
    }

    prompt = (
        f"You are drafting a RESEARCH DRAFT (not a final publication) for Project Parallax on: {topic['name']}. "
        f"Use ONLY this dataset — do not invent additional numbers: {verified_data}. "
        "STRICT RULES:\n"
        "1. If 'arxiv_source_found' is false, explicitly state 'No verified source found for this claim' — "
        "do NOT present the topic as settled fact.\n"
        "2. Avoid definitive verbs like 'proves', 'confirms', 'demonstrates conclusively'. Use "
        "'suggests', 'is consistent with', 'the study reports' instead, and attribute claims to their source.\n"
        "3. Include an HTML <table> showing the raw input metrics AND their 'data_type' "
        "(illustrative_model vs literature-sourced), plus the skeptic critique.\n"
        "4. Add a visible disclaimer <div> at the top stating: "
        "'AI-GENERATED DRAFT — PENDING HUMAN FACT-CHECK. Not for publication without review.'\n"
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

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        raise Exception(f"xAI API kļūda [{response.status_code}]: {response.text}")

    return response.json()["choices"][0]["message"]["content"]


def main():
    # 1. Izvēlas nejaušu tēmu
    topic = random.choice(TOPICS)

    # 2. Aģents 1: Datu ieguve un ilustratīvais modelis
    sim_results = agent_1_multi_source_simulation(topic)

    # 3. Aģents 2: Skeptiķa recenzija
    verified_data = agent_2_skeptic_evaluator(sim_results, topic)

    # 4. Aģents 3: HTML draft ģenerēšana
    html_content = agent_3_author_generator(topic, verified_data)

    # 5. Saglabā DRAFTU — NEVIS gatavu publikāciju
    # Mape "drafts/" NEDRĪKST būt saitēta no publiskās vietnes navigācijas / index.html
    drafts_dir = Path(REPO_PATH) / "myparallax_repo" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    base_filename = f"draft-{topic['id']}-{timestamp}"
    html_path = drafts_dir / f"{base_filename}.html"
    meta_path = drafts_dir / f"{base_filename}.meta.json"

    content_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()[:12]

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

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
        "human_reviewed": False,
        "review_status": "pending",
        "reviewer": None,
        "review_notes": None,
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"[*] DRAFTS saglabāti (NAV publicēti): {html_path}")
    print(f"[*] Metadati: {meta_path}")
    print("[*] Nākamais solis: cilvēka pārbaude ar review_cli.py, tad pārvietošana uz posts/.")


if __name__ == "__main__":
    main()
