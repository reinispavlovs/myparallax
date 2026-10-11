// POST /api/submit  -- receives a proposed study from the public form and files it
// as an issue in a (preferably private) GitHub repository, where a human reviews it.
// Nothing submitted here is published or changes any figure automatically.
//
// Environment variables (Vercel -> Project Settings -> Environment Variables):
//   GITHUB_TOKEN       fine-grained token with "Issues: Read and write" on the submissions repo ONLY
//   SUBMISSIONS_REPO   "owner/name" of the repo that receives the issues
//   CROSSREF_MAILTO    optional contact e-mail for Crossref's polite pool

const TOPICS = ['consciousness_independence_nde', 'megalithic_engineering_acoustics',
  'cyclical_cataclysms_precession', 'neural_cosmic_isomorphism'];
const STEPS = ['1', '2', '3', '4', 'side'];
const STANCES = ['supports', 'challenges', 'context'];
const MAX = { note: 600, name: 160, email: 200 };
const MIN_FORM_SECONDS = 4;

const hits = new Map(); // best-effort per-instance rate limit
function rateLimited(ip) {
  const now = Date.now();
  const arr = (hits.get(ip) || []).filter(t => now - t < 10 * 60 * 1000);
  arr.push(now);
  hits.set(ip, arr);
  return arr.length > 5;
}

function normDoi(raw) {
  let d = String(raw || '').trim();
  d = d.replace(/^https?:\/\/(dx\.)?doi\.org\//i, '').replace(/^doi:\s*/i, '').trim();
  return /^10\.\d{4,9}\/[^\s]+$/i.test(d) ? d : null;
}
const clean = (s, n) => String(s == null ? '' : s).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '').trim().slice(0, n);
const md = s => String(s).replace(/[`*_>#\[\]|<]/g, c => '\\' + c);

async function crossref(doi) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 6000);
  try {
    const mailto = process.env.CROSSREF_MAILTO ? '?mailto=' + encodeURIComponent(process.env.CROSSREF_MAILTO) : '';
    const r = await fetch('https://api.crossref.org/works/' + encodeURIComponent(doi) + mailto, { signal: ctrl.signal });
    if (r.status === 404) return { found: false };
    if (!r.ok) return { found: null };
    const m = (await r.json()).message || {};
    const year = (m.issued && m.issued['date-parts'] && m.issued['date-parts'][0] && m.issued['date-parts'][0][0]) || null;
    const authors = (m.author || []).slice(0, 4).map(a => [a.family, a.given && a.given[0]].filter(Boolean).join(' ')).join(', ');
    return { found: true, title: (m.title && m.title[0]) || '', journal: (m['container-title'] && m['container-title'][0]) || '', year, authors };
  } catch (e) {
    return { found: null };
  } finally { clearTimeout(timer); }
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') return res.status(405).json({ error: 'method_not_allowed' });
  try {
    const host = req.headers.host || '';
    const origin = req.headers.origin || '';
    if (origin && !origin.includes(host)) return res.status(403).json({ error: 'forbidden' });

    const ip = String((req.headers['x-forwarded-for'] || '').split(',')[0] || 'unknown').trim();
    if (rateLimited(ip)) return res.status(429).json({ error: 'rate_limited' });

    const b = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
    if (b.website) return res.status(200).json({ ok: true }); // honeypot: pretend success
    if (typeof b.elapsed === 'number' && b.elapsed < MIN_FORM_SECONDS) return res.status(400).json({ error: 'too_fast' });

    const topic = String(b.topic || '');
    const step = String(b.step || '');
    const stance = String(b.stance || '');
    if (!TOPICS.includes(topic)) return res.status(400).json({ error: 'bad_topic' });
    if (!STEPS.includes(step)) return res.status(400).json({ error: 'bad_step' });
    if (!STANCES.includes(stance)) return res.status(400).json({ error: 'bad_stance' });
    if (b.consent !== true) return res.status(400).json({ error: 'consent_required' });

    const doi = normDoi(b.doi);
    if (!doi) return res.status(400).json({ error: 'bad_doi' });
    const note = clean(b.note, MAX.note);
    if (note.length < 20) return res.status(400).json({ error: 'note_too_short' });
    const name = clean(b.name, MAX.name);
    const email = clean(b.email, MAX.email);
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return res.status(400).json({ error: 'bad_email' });

    const token = process.env.GITHUB_TOKEN, repo = process.env.SUBMISSIONS_REPO;
    if (!token || !repo || !/^[\w.-]+\/[\w.-]+$/.test(repo)) {
      console.error('[submit] GITHUB_TOKEN or SUBMISSIONS_REPO not configured');
      return res.status(503).json({ error: 'not_configured' });
    }

    const cr = await crossref(doi);
    if (cr.found === false) return res.status(400).json({ error: 'doi_not_found' });

    const record = { topic, step, stance, doi, note, contributor: name, crossref: cr.found ? { title: cr.title, journal: cr.journal, year: cr.year, authors: cr.authors } : null, submitted_at: new Date().toISOString() };
    const title = '[Submission] ' + (cr.title ? cr.title.slice(0, 100) : doi);
    const body = [
      `**Topic:** ${topic}  \n**Step:** ${step}  \n**Stance:** ${stance}`,
      `**DOI:** https://doi.org/${doi}  \n**Crossref:** ${cr.found ? md(`${cr.title} (${cr.authors}; ${cr.journal} ${cr.year || ''})`) : 'not verified (Crossref unavailable)'}`,
      `**Why it matters (submitter):**\n\n> ${md(note).replace(/\n/g, '\n> ')}`,
      `**Contributor (public if accepted):** ${name ? md(name) : '(anonymous)'}  \n**Private contact:** ${email ? md(email) : '(none)'}`,
      '---',
      'Review checklist: DOI resolves, claim matches the paper, stance is fair, no conflict of interest hidden. ' +
      'Accepting does not change any percentage by itself.',
      '<details><summary>machine-readable</summary>\n\n```json\n' + JSON.stringify(record, null, 2) + '\n```\n</details>'
    ].join('\n\n');

    const gh = await fetch(`https://api.github.com/repos/${repo}/issues`, {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json', 'Content-Type': 'application/json', 'User-Agent': 'project-parallax-submit', 'X-GitHub-Api-Version': '2022-11-28' },
      body: JSON.stringify({ title, body, labels: ['submission', 'topic:' + topic] })
    });
    if (!gh.ok) {
      console.error('[submit] GitHub responded', gh.status);
      return res.status(502).json({ error: 'upstream_failed' });
    }
    return res.status(200).json({ ok: true, verified: cr.found === true });
  } catch (e) {
    console.error('[submit] exception', e && e.message);
    return res.status(500).json({ error: 'server_error' });
  }
};
module.exports._normDoi = normDoi;
