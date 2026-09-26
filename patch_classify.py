import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = re.compile(r"def call_llm_classify_batch\(prompt: str\) -> str:.*?\n\ndef agent_1_corpus_analysis", re.DOTALL)

new_func = '''def call_llm_classify_batch(texts):
    """Batch classifier for corpus abstracts. Sends up to ~10 texts at once,
    expects a JSON array of category labels back, one per input text."""
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}",
    }
    numbered = "\\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
    prompt = (
        "Classify each numbered abstract below into EXACTLY one category: "
        "supports_veridical, null_result, neuro_mechanism, inconclusive.\\n"
        "supports_veridical = evidence supporting veridical or anomalous perception.\\n"
        "null_result = study found no effect or no support.\\n"
        "neuro_mechanism = explains via known neuro or physiological mechanism.\\n"
        "inconclusive = ambiguous, unrelated, or insufficient info.\\n\\n"
        "Abstracts:\\n" + numbered + "\\n\\n"
        f"Return ONLY a JSON array of exactly {len(texts)} strings, one label per abstract, in order. "
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
        print(f"[WARN] classify_batch LLM call failed: {e}")
        return ["inconclusive"] * len(texts)


def agent_1_corpus_analysis'''

new_content, n = pattern.subn(new_func, content, count=1)
if n != 1:
    print("PATCH FAILED n=" + str(n))
else:
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("PATCH OK")
