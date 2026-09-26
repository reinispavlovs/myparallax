import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = re.compile(r"def call_llm_classify_batch\(texts\):.*?\n\ndef agent_1_corpus_analysis", re.DOTALL)

new_func = (
    "def call_llm_classify_batch(texts):\n"
    "    url = \"https://api.x.ai/v1/chat/completions\"\n"
    "    headers = {\n"
    "        \"Content-Type\": \"application/json\",\n"
    "        \"Authorization\": \"Bearer \" + XAI_API_KEY,\n"
    "    }\n"
    "    numbered = chr(10).join(str(i+1) + \". \" + t for i, t in enumerate(texts))\n"
    "    prompt = (\n"
    "        \"Classify each numbered abstract below into EXACTLY one category: \"\n"
    "        \"supports_veridical, null_result, neuro_mechanism, inconclusive.\" + chr(10) +\n"
    "        \"supports_veridical = evidence supporting veridical or anomalous perception.\" + chr(10) +\n"
    "        \"null_result = study found no effect or no support.\" + chr(10) +\n"
    "        \"neuro_mechanism = explains via known neuro or physiological mechanism.\" + chr(10) +\n"
    "        \"inconclusive = ambiguous, unrelated, or insufficient info.\" + chr(10) + chr(10) +\n"
    "        \"Abstracts:\" + chr(10) + numbered + chr(10) + chr(10) +\n"
    "        \"Return ONLY a JSON array of exactly \" + str(len(texts)) + \" strings, one label per abstract, in order. \"\n"
    "        \"No markdown, no explanation.\"\n"
    "    )\n"
    "    payload = {\n"
    "        \"model\": \"grok-4.6\",\n"
    "        \"messages\": [\n"
    "            {\"role\": \"system\", \"content\": \"You output ONLY valid JSON. No markdown, no prose.\"},\n"
    "            {\"role\": \"user\", \"content\": prompt},\n"
    "        ],\n"
    "        \"temperature\": 0.0,\n"
    "    }\n"
    "    try:\n"
    "        r = requests.post(url, headers=headers, json=payload, timeout=60)\n"
    "        r.raise_for_status()\n"
    "        raw = r.json()[\"choices\"][0][\"message\"][\"content\"].strip()\n"
    "        raw = re.sub(r\"^```(json)?|```$\", \"\", raw, flags=re.MULTILINE).strip()\n"
    "        labels = json.loads(raw)\n"
    "        if not isinstance(labels, list):\n"
    "            raise ValueError(\"not a list\")\n"
    "        return labels\n"
    "    except Exception as e:\n"
    "        print(\"[WARN] classify_batch LLM call failed: \" + str(e))\n"
    "        return [\"inconclusive\"] * len(texts)\n"
    "\n"
    "\n"
    "def agent_1_corpus_analysis"
)

new_content, n = pattern.subn(new_func, content, count=1)
if n != 1:
    print("PATCH FAILED n=" + str(n))
else:
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("PATCH OK")
