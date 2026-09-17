export default async function handler(req, res) {
    // Atļaujam tikai POST pieprasījumus
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    const { history } = req.body;
    const apiKey = process.env.GEMINI_API_KEY; // Paņem atslēgu no Vercel drošajiem iestatījumiem

    if (!apiKey) {
        return res.status(500).json({ error: 'GEMINI_API_KEY is not configured on Vercel' });
    }

    const systemInstruction = "You are the Project Parallax Core Intelligence — an analytical research assistant based on the framework 'More Real Than the Visible' by Reinis Pavlovs, embodying Alan Watts' wisdom.";

    try {
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                system_instruction: { parts: { text: systemInstruction } },
                contents: history
            })
        });

        const data = await response.json();
        
        if (data.candidates && data.candidates.length > 0) {
            const reply = data.candidates[0].content.parts[0].text;
            return res.status(200).json({ reply });
        } else {
            return res.status(500).json({ error: 'Invalid response from Gemini API' });
        }
    } catch (error) {
        console.error("Gemini API Error:", error);
        return res.status(500).json({ error: 'Failed to communicate with Core Intelligence' });
    }
}