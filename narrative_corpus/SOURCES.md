# Narrative corpus: source access log (public part)

Only sources that are open, or that have replied, are described here. Other candidate sources appear on the Tribunal page as "Source N" until they reply. This is a working policy, not legal advice; the EU text-and-data-mining position in SPEC.md section 2 applies.

## NDERF (nderf.org): `tdm_open` since 2026-10-17
- `robots.txt` returns 404 on nderf.org and www.nderf.org (checked 2026-10-17).
- Disclaimer: a notice that suicide NDEs are posted for research only, and a copyright line saying submitters warrant they may grant reproduction on the website. Privacy page: nothing on reuse or automated access.
- Pilot by derived statistics only: no excerpts, no names. Collection is slow and identified (`scripts/ingest_nderf.py`); private copies stay outside git. If NDERF objects, collection stops and derived data are removed.
- Each NDERF account is a fixed questionnaire (about 45 closed items with Yes / No / Uncertain or graded answers) plus free text. The corpus uses the closed items as codes (`narrative_corpus/codebook.json`, read by rule in `scripts/parse_nderf.py`), not model judgement. Free text is not used and not stored. Answers are solicited self-reports. NDERF's own classification label is kept; the headline group is the label "NDE" only.
- "Aware of events elsewhere: yes, and the facts have been checked" is stored as a narrator-only claim, which counts as unverifiable under our rule (only `independent_document` or `independent_witness` can confirm).
- Suicide-related accounts are not shown or quoted. Their closed answers are counted in aggregates only.
- Contact: Dr Jeffrey Long (NDERF) replied in October 2026 with suggested publications. On 2026-10-22 he agreed that we may say publicly that he replied and suggested them. He did not state a position on reuse of NDERF data, and his reply is not an endorsement of this project.
