// POST /api/submit  -- receives a proposed study from the public form and files it
// as an issue in a (preferably private) GitHub repository, where a human reviews it.
// Nothing submitted here is published or changes any figure automatically.
//
// Environment variables (Vercel -> Project Settings -> Environment Variables):
//   GITHUB_TOKEN       fine-grained token with "Issues: Read and write" on the submissions repo ONLY
//   SUBMISSIONS_REPO   "owner/name" of the repo that receives the issues
//   CROSSREF_MAILTO    optional contact e-mail for Crossref's polite pool
//
// Accepted references: DOI (verified against Crossref, then DataCite for Zenodo/OSF/arXiv DOIs),
// arXiv id or link, ISBN-10/13, or any https link. Non-DOI references are NOT verified
// automatically; the issue says so and the reviewer must open them.

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
function isbnOk(d) {
  if (d.length === 10) {
    let s = 0;
    for (let i = 0; i < 10; i++) {
      const c = d[i];
      const v = (c === 'X' && i === 9) ? 10 : (/\d/.test(c) ? Number(c) : NaN);
      if (Number.isNaN(v)) return false;
      s += v * (10 - i);
    }
    return s % 11 === 0;
  }
  if (d.length === 13 && /^\d{13}$/.test(d)) {
    let s = 0;
    for (let i = 0; i < 13; i++) s += Number(d[i]) * (i % 2 ? 3 : 1);
    return s % 10 === 0;
  }
  return false;
}
function parseRef(raw) {
  const t = String(raw || '').trim().slice(0, 300);
  if (!t) return null;
  const doi = normDoi(t);
  if (doi) return { kind: 'doi', id: doi, url: 'https://doi.org/' + doi };
  const ax = t.match(/^(?:https?:\/\/arxiv\.org\/(?:abs|pdf)\/|arxiv:\s*)([a-z\-]+(?:\.[A-Za-z]{2})?\/\d{7}|\d{4}\.\d{4,5})(v\d+)?(?:\.pdf)?\/?$/i);
  if (ax) { const id = ax[1] + (ax[2] || ''); return { kind: 'arxiv', id, url: 'https://arxiv.org/abs/' + id }; }
  const ib = t.replace(/^isbn(?:-1[03])?:?\s*/i, '').replace(/[\s-]/g, '').toUpperCase();
  if (/^(\d{9}[\dX]|\d{13})$/.test(ib) && isbnOk(ib)) return { kind: 'isbn', id: ib, url: 'https://openlibrary.org/isbn/' + ib };
  if (/^https:\/\/\S+$/i.test(t)) {
    try { const u = new URL(t); if (u.hostname.includes('.')) return { kind: 'url', id: u.href, url: u.href }; } catch (e) { /* not a url */ }
  }
  return null;
}
const clean = (s, n) => String(s == null ? '' : s).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '').trim().slice(0, n);
const md = s => String(s).replace(/[`*_>#\[\]|<]/g, c => '\\' + c);

async function crossref(doi) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 4000);
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

async function datacite(doi) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 4000);
  try {
    const r = await fetch('https://api.datacite.org/dois/' + encodeURI(doi), { signal: ctrl.signal });
    if (r.status === 404) return { found: false };
    if (!r.ok) return { found: null };
    const a = ((await r.json()).data || {}).attributes || {};
    const authors = (a.creators || []).slice(0, 4).map(c => c.familyName ? [c.familyName, c.givenName && c.givenName[0]].filter(Boolean).join(' ') : (c.name || '')).filter(Boolean).join(', ');
    const pub = a.publisher && (a.publisher.name || a.publisher);
    return { found: true, title: (a.titles && a.titles[0] && a.titles[0].title) || '', journal: typeof pub === 'string' ? pub : '', year: a.publicationYear || null, authors };
  } catch (e) {
    return { found: null };
  } finally { clearTimeout(timer); }
}

// Crossref first, DataCite second (Zenodo, OSF and arXiv DOIs live there).
async function lookupDoi(doi) {
  const c = await crossref(doi);
  if (c.found === true) return c;
  const d = await datacite(doi);
  if (d.found === true) return d;
  if (c.found === false && d.found === false) return { found: false };
  return { found: null };
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

    const ref = parseRef(b.ref != null ? b.ref : b.doi);
    if (!ref) return res.status(400).json({ error: 'bad_ref' });
    const doi = ref.kind === 'doi' ? ref.id : null;
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

    let cr = { found: null };
    if (doi) {
      cr = await lookupDoi(doi);
      if (cr.found === false) return res.status(400).json({ error: 'doi_not_found' });
    }

    const record = { topic, step, stance, ref, doi, note, contributor: name, lookup: cr.found ? { title: cr.title, journal: cr.journal, year: cr.year, authors: cr.authors } : null, submitted_at: new Date().toISOString() };
    const title = '[Submission] ' + (cr.title ? cr.title.slice(0, 100) : ref.id.slice(0, 100));
    const refLine = doi
      ? `**DOI:** ${ref.url}  \n**Registry lookup (Crossref/DataCite):** ${cr.found ? md(`${cr.title} (${cr.authors}; ${cr.journal} ${cr.year || ''})`) : 'not verified (registry unavailable)'}`
      : `**Reference (${ref.kind}):** ${md(ref.id)}  \n**Link:** ${ref.url}  \n⚠️ **Not verified automatically.** Open the link and confirm that it exists, who wrote it, and that it says what the submitter claims.`;
    const body = [
      `**Topic:** ${topic}  \n**Step:** ${step}  \n**Stance:** ${stance}`,
      refLine,
      `**Why it matters (submitter):**\n\n> ${md(note).replace(/\n/g, '\n> ')}`,
      `**Contributor (public if accepted):** ${name ? md(name) : '(anonymous)'}  \n**Private contact:** ${email ? md(email) : '(none)'}`,
      '---',
      'Review checklist: reference resolves, claim matches the work, stance is fair, no conflict of interest hidden. ' +
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
    return res.status(200).json({ ok: true, verified: Boolean(doi) && cr.found === true });
  } catch (e) {
    console.error('[submit] exception', e && e.message);
    return res.status(500).json({ error: 'server_error' });
  }
};
module.exports._normDoi = normDoi;
module.exports._parseRef = parseRef;
