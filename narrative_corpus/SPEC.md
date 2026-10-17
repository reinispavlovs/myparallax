# Narrative Corpus: specification v0.1 (draft)

Status: draft v0.2 for the author's review (access rules revised). Nothing here is implemented yet. No data has been collected.

## 1. Purpose

Project Parallax has one evidence layer today, the **Study corpus** (published studies). This document defines a second, parallel layer, the **Narrative corpus** (first-person and reported accounts), measured with its own methods.

The two layers answer different questions and are never merged into one number.

| Layer | Question it answers |
|---|---|
| Study corpus | What do published studies show? Which mechanisms are proposed? |
| Narrative corpus | What do experiencers consistently report? How independent are the reports? How many contain checkable claims? How many of those check out? |

Principle: one account is subjective. A large, structured set of accounts is an analysable dataset. We measure it before deciding what it means.

Out of scope for v0.1: any weight in the calculator, any change to checklist percentages.

## 2. Sources and access rules

Pilot sources, in this order: 1. NDERF  2. IANDS  3. Jeff Mara podcast  4. ComingHome  5. Antony productions

**Method.** Project Parallax reads publicly accessible accounts and computes **derived statistics** from them (motif frequencies, n_raw, n_eff, checkable claims, verification outcomes). It does not republish source texts. The same logic as for the Study corpus: sources are named and linked, only short excerpts are shown, the analysis is ours.

**Two things are kept separate:**
1. Reading, briefly quoting and analysing public content. This is the project's method.
2. Mass download and republication of full texts. This is **not** a goal and is never done.

To analyse a text it has to be fetched at least once. The fetched text is a private working copy, never published and never committed to the repository.

**Before collecting from any source, record its `access_status`:**
- `tdm_open`: lawful public access, no machine-readable reservation (robots.txt, meta tags) and no terms forbidding automated access were found.
- `restricted`: robots.txt or the terms of use forbid automated access. Not crawled. Only manual reading of individual pages and short cited excerpts, or the rights holder is asked.
- `permission_granted`: the rights holder agreed in writing (for example to share a structured export).
- `unknown`: not yet checked. Nothing is collected.

**How collection is done:** identified user agent, polite rate limit, no login walls bypassed, no scraping around a reservation. A rights holder who objects is respected: collection stops and derived records from that source are removed.

**What is published:** codes, hashes, excerpts of at most 300 characters with attribution and a link, aggregate statistics. **What is not:** full texts, narrator identities.

**Permission** is therefore not a precondition where `tdm_open` holds. It is still worth asking because the rights holder may offer a structured export, may correct our reading, and a source that agrees is a stronger citation than one that was only read.

Note: this is a working policy, not legal advice. In the EU the text-and-data-mining exception (Directive (EU) 2019/790, Art. 4) covers analysis of lawfully accessible content unless rights were reserved in a machine-readable way; it is implemented in national law. Confirm with a lawyer once, before scaling beyond the pilot.

## 3. Record (one per account)

See `schema.json`. Summary:

- **Provenance**: source, URL, retrieved_at, published_at, event date (if stated), access_status.
- **Account type**: `first_hand` | `second_hand` | `retelling` | `interview_transcript`. Second-hand and retellings are stored but not counted in n_eff unless the original is absent from the set.
- **Narrator**: pseudonymous id only (a salted hash of the source handle). No names, no contact data, no health details beyond a coarse context (cardiac arrest, surgery, accident, illness, unknown).
- **Collection context**: `solicited` (true if the narrator answered a structured form or interview prompt, which shapes what is reported), `delay_to_report` (time between event and account, if known).
- **Text**: `text_hash` and an excerpt of at most 300 characters. The full fetched text is a private working copy, kept outside the repository, only as long as needed to code and verify.
- **Duplicates**: `cluster_id` and `duplicate_of`, with the method used (exact text, near-duplicate, same narrator across sources, retelling of a known account).
- **Motifs**: list of codes from the frozen codebook, each with coder (`llm` | `human`) and confidence.
- **Claims**: zero or more checkable claims per account (see 5).
- **Coding metadata**: codebook version, coder id, date.

## 4. Measures (all reported per source and pooled)

- `n_raw`: number of accounts collected.
- `n_eff`: effective number of independent first-hand accounts after removing duplicates, retellings and same-narrator repeats. The method and the clusters are published.
- Motif frequency: share of the n_eff accounts containing each motif, with a 95% interval (Wilson). Never a bare percentage.
- Checkable-claim rate: accounts with at least one checkable claim / n_eff.
- Verification outcomes, counted per claim: `confirmed` | `refuted` | `unverifiable` | `not_attempted`.
- Coding reliability: agreement (Cohen's kappa) between the LLM coder and a human on a double-coded subsample, per motif. A motif with kappa below 0.6 is reported as "low reliability".

Always shown next to the numbers: who collected the accounts, whether they were solicited, and the known biases (self-selection, cultural expectation, memory reconstruction, social copying between accounts).

## 5. Claims and verification

A claim is **checkable** only if an outside source could in principle confirm or refute it (a specific event, object, conversation, time or place the narrator could not have known by ordinary means).

Each claim stores `evidence_type`:
- `independent_document` (medical or other record)
- `independent_witness`
- `same_narrator_only` (the narrator also says it was confirmed; this is **not** counted as `confirmed`)
- `none`

`confirmed` requires `independent_document` or `independent_witness`. A claim that is confirmed only by the narrator is stored as `unverifiable`, with the narrator's statement kept in the note. This one rule prevents most inflated confirmation counts.

## 6. Codebook

Frozen before coding begins (v0.1 will be written together with the author, using Greyson's NDE Scale items and the motifs already named in the NDE article as the starting list). Changes create a new version. Old codings keep their version.

## 7. Pilot (the first measurement, no conclusions)

1. Record `access_status` for each pilot source (robots.txt, terms). Start with the source that has the clearest terms. Where a source is `restricted`, ask or skip; where it is `tdm_open`, optionally still tell the rights holder what we are doing.
2. Collect about 200 accounts from that source politely and without republishing.
3. Code with the LLM, then the author double-codes 50 at random. Compute kappa per motif.
4. Publish the pilot report: n_raw, n_eff, motif frequencies with intervals, checkable-claim rate, verification outcomes, reliability, and a list of everything that went wrong.
5. Only then decide whether the method is good enough to scale.

## 8. Publication

- A separate card in the Tribunal: "Narrative corpus (reports, not proof)", with the measures above.
- Raw derived data in `narrative_corpus/data/` (codes, hashes, excerpts); full texts are not published.
- Every report is versioned and listed in the Archive like articles.
- Mistakes are logged in the corrections log.

## 9. Ethics and privacy

- Accounts are about illness and near-death. Treat them as sensitive even when public.
- No narrator identification attempts, no linking across sources by identity beyond duplicate detection.
- A narrator or rights holder can ask for removal at any time. It is done without discussion and logged.
- No medical or life advice is derived from this data.

## 10. Later (not now)

Integration with the calculator is decided only after the pilot. If it happens, the narrative corpus enters as its own status with its own inputs (n_eff, consistency, verified-claim rate), not as a weight on the study corpus.

## 11. Health-outcome cases (evidence ladder)

Some accounts report a medical outcome (recovery, remission, no change, death). These are stored in the optional `medical_case` block and never mixed into the motif statistics. The goal is to show **how well each case is documented**, not to say what works.

**Documentation ladder** (lowest to highest). Counts are always reported per level and never pooled across levels:
1. `self_report`: the person says so.
2. `interview`: said in a recorded interview, nothing else checked.
3. `clinician_statement`: a named clinician states it.
4. `records_seen_by_reviewer`: diagnosis and outcome records were seen by a qualified reviewer.
5. `records_published`: records are published or deposited.
6. `independent_specialist_review`: an independent specialist reviewed the records.
7. `published_case_report`: peer-reviewed case report.
8. `controlled_study`: controlled or registry-based study.

**Rules**
- **Diagnosis basis is stored separately.** For cancer, histology or imaging counts; "I was told" is `unconfirmed`.
- **Confounders are recorded**: concurrent conventional treatment (`conventional_treatment_concurrent`), follow-up length, relapse. A recovery during conventional treatment is not attributed to anything else.
- **Failures are counted too.** `no_change`, `deterioration` and `death` are valid outcomes. Where a denominator exists (a registry, a clinic series), it is recorded (`denominator_known`). Without it, the page says plainly that favourable cases are over-represented in what is public (survivorship and media selection) and no rate is computed.
- **Spontaneous remission** is a documented but rare phenomenon in the literature. It is the null explanation to be addressed for every remission case, not an afterthought.
- **No recommendations.** Output is evidence status per intervention type ("what the documentation shows"), with the strongest evidence on both conventional and alternative approaches shown side by side. No dosing, protocols or "this works for you".
- **Human review is mandatory** (`reviewed_by_human: true`) before any health case is published. Automated coding can propose, not publish.
- Every health card carries the line: "Evidence status only. Not medical advice. Do not change treatment because of this page; talk to your clinician."
- Named public figures (authors, speakers) are described only by what they have publicly said and what has been independently documented, with the documentation level shown. Unverified statements are labelled as such.
- A person's own claim of verification does not raise the level above `self_report` or `interview`.
