# Narrative corpus: source access log

Checked 2026-10-12 by reading the public pages (not legal advice; the EU text-and-data-mining position in SPEC.md section 2 still applies). robots.txt: NDERF none (404). IANDS only disallows /wp-admin/. Updated 2026-10-17 after reading the NDERF disclaimer and the IANDS Rights and Usage FAQ.

| Source | What it is | What the pages say | access_status (provisional) | Next action |
|---|---|---|---|---|
| NDERF (nderf.org) | 16,000+ experiences (NDERF, OBERF, ADCRF), mostly from structured questionnaires; public versions "lightly edited for clarity" | `robots.txt` returns 404 on both nderf.org and www.nderf.org (checked 2026-10-17). Disclaimer (`/disclaimer.htm`): a notice that suicide NDEs are posted for research only, and a copyright line saying submitters warrant they may grant reproduction on the website. Privacy page: personal data not shared; nothing on reuse or automated access. | `tdm_open` (2026-10-17) | Pilot by derived statistics only. No excerpts, no names. Dr Long was contacted earlier (no reply yet); if NDERF objects, collection stops and derived data are removed. Suicide-related accounts are held back from coding until a human reviews them. |
| IANDS (iands.org) | Registry of personal NDE accounts, anonymous, minor edits; separate video/audio accounts (mostly on YouTube) | Copyright 2026 IANDS, all rights reserved. "IANDS cannot grant permission to publish quotations from these NDE accounts" (it has no permission from the authors). Points to fair use. No statement on automated access. | `restricted` for republication | Store derived statistics only: set `excerpt` to null for IANDS records. Ask IANDS in writing before any collection. Asked 2026-10-17; no reply yet. Rights FAQ and disclaimer say nothing about automated reading or analysis. |
| YouTube: Jeff Mara (UC_c8KysI2G9rAbNyD1dVd6g) | Interviews | Video rights belong to the channel owner. As I understand YouTube's terms, downloading or scraping outside the API is not allowed. | `restricted` (technical and rights) | No scraping, no transcripts. Option: hand-code a small sample from watching (metadata + motif codes only), or ask the owner for permission/transcripts. |
| YouTube: Anthony Chene Production (@AnthonyCheneProduction) | Interviews / videos | As above | `restricted` | As above |
| YouTube: Coming Home (@cominghomechannel) | Interviews / videos | As above | `restricted` | As above |
| YouTube: ThanatosTV EN (@ThanatosTVEN) | Interviews / videos | As above | `restricted` | As above |

## Pilot decision (proposed)
1. Text pilot: NDERF (`tdm_open` since 2026-10-17). First run about 200 accounts with `scripts/ingest_nderf.py` on the author's computer; private copies stay in `narrative_corpus_private/` (git-ignored). Derived stats only.
2. Fallback or parallel: hand-coded sample of about 30 YouTube interviews to test the codebook (no transcripts stored).
3. IANDS: no collection until IANDS replies.

## NDERF structure (found 2026-10-17)
Each NDERF account is a fixed questionnaire (about 45 closed items such as "Did you pass into or through a tunnel?" with Yes / No / Uncertain or graded answers) plus free-text fields. The narrative corpus therefore uses the closed items as its codes (`narrative_corpus/codebook.json`, rule-read by `scripts/parse_nderf.py`), not model judgement. Free text is not used and not stored. The answers are solicited self-reports; NDERF's own classification (NDE, Probable NDE, STE, ADC, ...) is kept and the headline group is the label "NDE" only. "Aware of events elsewhere: yes, and the facts have been checked" is stored as a narrator-only claim (unverifiable by our rule).
