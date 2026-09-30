const MODELS = ['gemini-1.5-flash', 'gemini-1.5-pro'];
const MAX_RETRIES_PER_MODEL = 2;
const BASE_DELAY_MS = 1500;

const SYSTEM_INSTRUCTION = `Tu esi "Project Parallax" kodols — sarunu biedrs un ceļvedis. Šī projekta pamatā ir grāmatas «Reālāks par redzamo» idejas, kuras autors ir Reinis Pavlovs. Tavs fokuss: apziņas pētījumi (NDE/OBE), realitātes daba, cilvēces alternatīvā vēsture — caur "paralakses metodi" (skatupunkta maiņu). Atbildes veido TIEŠAS, konkrētas un uz punktu — izvairies no gariem filozofiskiem ievadiem vai atkārtotām metaforām, ja lietotājs nav lūdzis filozofisku pārdomu. Atbildi lietotāja valodā; pēc noklusējuma – angliski.`;

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const { history } = req.body;

    if (!history || !Array.isArray(history)) {
      return res.status(400).json({ error: "Missing or invalid history array in request body." });
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      console.error("[FATAL] GEMINI_API_KEY is missing in environment variables.");
      return res.status(500).json({ error: "Server misconfiguration: missing API key." });
    }

    let lastError = null;

    for (const model of MODELS) {
      for (let attempt = 1; attempt <= MAX_RETRIES_PER_MODEL; attempt++) {
        try {
          const url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent?key=" + apiKey;

          const payload = {
            contents: history,
            systemInstruction: {
              parts: [{ text: SYSTEM_INSTRUCTION }]
            }
          };

          const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });

          const data = await response.json();

          if (response.ok) {
            console.log("[SUCCESS] Model: " + model + ", Attempt: " + attempt);
            return res.status(200).json(data);
          }

          if (response.status === 503 || response.status === 429) {
            console.warn("[RETRY] Model: " + model + ", Attempt: " + attempt + "/" + MAX_RETRIES_PER_MODEL + " - Status " + response.status);
            lastError = data.error || { message: "Service Unavailable (" + response.status + ")" };
            if (attempt < MAX_RETRIES_PER_MODEL) {
              await sleep(BASE_DELAY_MS * attempt);
              continue;
            }
          } else if (response.status === 404) {
            console.warn("[FALLBACK] Model: " + model + " not found (404). Trying next model.");
            lastError = data.error || { message: "404 Not Found" };
            break;
          } else {
            console.error("[ERROR] Model: " + model + ", Status: " + response.status, data.error);
            lastError = data.error || { message: "HTTP " + response.status };
            break;
          }

        } catch (err) {
          console.error("[EXCEPTION] Model: " + model + ", Attempt: " + attempt, err.message);
          lastError = { message: err.message };
          if (attempt < MAX_RETRIES_PER_MODEL) {
            await sleep(BASE_DELAY_MS * attempt);
          }
        }
      }
    }

    console.error("[FATAL] All models and retries exhausted.", lastError);
    return res.status(502).json({
      error: "All Gemini models failed or are unavailable.",
      details: lastError
    });

  } catch (outerErr) {
    console.error("[CRITICAL EXCEPTION in handler]:", outerErr);
    return res.status(500).json({ error: "Internal Server Error: " + outerErr.message });
  }
};