---
title: "Design — Eval Set Rebalance"
type: spec
term: AY2526-T3
subject: STSP001-Industry-Invited-Lectures
owner: Nian (Domain Expert)
updated: 2026-08-07
tags: [capstone, kalasag, eval, dataset, measurement, spec]
---

# Design — Eval Set Rebalance

**Owner:** Nian (Domain Expert) · **Consumes:** `backend/eval/run_eval.py` · **Affects:** `eval-set-candidate-55.csv`, `knowledge-base/out/kb.sqlite`

This spec fixes a measurement problem: `eval-set-candidate-55.csv` cannot distinguish the Kalasag pipeline from a one-line regex. It also repairs three integrity defects in the file and one retrieval leak in the KB.

## The problem

In the current 55 messages, link presence and gold label are almost perfectly correlated.

| | no link | has link |
|---|---|---|
| **SCAM** | 1 | 32 |
| **LEGIT** | 18 | 0 |

`if has_link: SCAM` therefore scores **accuracy 0.980, precision 1.000, recall 0.970, F1 0.985** on the deduplicated set — with zero LLM calls. Any number `run_eval.py` reports is confounded: we have no evidence the LangGraph pipeline outperforms `grep`.

> **These counts are hand-assigned and they corrected an earlier estimate.** Three successive automated detectors put the link-free SCAM count at 3; reading all 51 messages put it at 1. The detectors missed `.ai`, `.vin`, `.tw`, `.by`, and `.cz` domains. The correlation is *tighter* than automated measurement showed, and the baseline correspondingly higher — 0.985, not the 0.952 first reported.

This is the question a panelist will ask, and today we cannot answer it.

## Objectives

1. Break the link/label correlation so the eval measures the pipeline rather than a surface feature.
2. Repair the integrity defects that make the current numbers wrong regardless of composition.
3. Publish the regex baseline alongside the pipeline result, so the confound is a declared control instead of a hole.

## Non-goals

- **Email and bare-URL inputs.** `preprocess.detect_message_type` has three branches and the eval exercises one. The corpus is SMS-only, so covering the other two means authoring synthetic messages — the weak-evidence move this spec exists to avoid everywhere else. Record as a stated limitation in `docs/PRD.md` instead.
- **A second full `en` eval pass.** ~4 LLM calls/message; doubling the run for a language check is not worth the sandbox quota one week out. See [Language coverage](#language-coverage).
- **Re-labelling the whole corpus.** The label-noise finding below is scoped to the messages this spec touches.
- Any change to the graph, prompts, or UI.

---

## Target composition

n = 85: keep all 51 unique existing messages, add 34.

**As built** (hand-verified after adding the rows):

| | no link | has link | total |
|---|---|---|---|
| **SCAM** | 1 **+12** = 13 | 32 | 45 |
| **LEGIT** | 18 **+2** = 20 | **+20** = 20 | 40 |

Regex baseline falls **F1 0.985 → 0.660** (accuracy 0.612, precision 0.615, recall 0.711). Class balance improves from 33/18 to 45/40.

The LEGIT additions were drawn as 22 link-bearing rows, but reading each one moved two into the link-free column: M070's only address is an email (`basecamp@powermaccenter.com`) and M074 refers to "the UnionBank website" in prose without giving it. Both remain useful hard negatives; they just land in the other stratum, leaving LEGIT at an even 20/20.

Keeping all 51 is deliberate. It lets the write-up report old-set and new-set side by side and show the baseline collapse, which is a stronger result than any single accuracy figure — and it forecloses the "did you drop the ones you failed?" question.

### Why stratified, not representative

This set oversamples hard cases on purpose. A test set's job is to **discriminate between systems**, not to estimate field prevalence. The reported F1 is therefore a discrimination score, not a prediction of live accuracy, and the write-up must say so in those words. Reporting a stratified number as if it were a prevalence estimate is the mistake this note exists to prevent.

---

## The additions

### 12 link-free SCAMs — curated, not sampled

The pool is far smaller than it first appears. Of 692 unheld SCAM messages, only **26** survive link detection, and those 26 break down as 13 usable, 3 that do carry links a detector missed, and 10 unusable (see [Label noise](#label-noise-in-the-corpus)). The 12 below are hand-picked from the 13; `msg01610` is the spare.

| id | type | why it is hard |
|---|---|---|
| `msg00408` | casino | Pure follow-up. No brand, no link, no offer detail — "Message mo na po ako para maguide kita manalo." The hardest item in the set. |
| `msg00174` | — | Rigged-game bait, Messenger handle, describes the sender's outfit to seem human. |
| `msg00282` | casino | Same pattern, leetspeak evasion (`Hell0`, `MEG@WIN`), FB contact. |
| `msg00407` | — | Same pattern, `sit3`/`makap@ld0` evasion, MSNGR handle. |
| `msg00696` | — | Rigged-game bait closing on "Reply ''YES'' po if interested." |
| `msg00546` | — | Telegram handle only; frames the scammer as a *guro* (mentor). |
| `msg00595` | — | 90 chars, cryptic, Telegram handle. Tests behaviour on near-zero signal. |
| `msg01610` | casino | Free umbrella/T-shirt/P200 + Telegram. *(spare)* |
| `msg01003` | — | UnionBank credit-card offer that reads exactly like a real ad until the Viber handle. |
| `msg01100` | loan | "Disregard if not interested. God Bless." — polite register, no pressure markers. |
| `msg01162` | loan | Sangla ORCR loan, plausible product, no link. |
| `msg01379` | loan | Names Security Bank, gives a mobile number and a contact person. |
| `msg01401` | loan | 85 chars, SMS-speak (`r u employed`), phone-only contact. |

**This class is the point of the exercise.** Chat-bait and "message me on Messenger" lures are the most likely thing an elderly Filipino actually receives, and the eval set contains **zero** of them today. They also carry no link, no impersonated brand, and no urgency deadline — none of the three signals the current set rewards.

Three link-free-looking candidates are excluded because they do carry a link every detector missed: `msg00965` (`bdo.mymobileapp.uk`, an OTP-harvesting BDO phish), `msg00710` (bare IP `38.11.89.109`), and `msg00659` (bare IP `8.212.168.…`). All three belong in the set, but in the link-bearing stratum, not this one.

### 22 link-bearing LEGITs — capped at 4 per vendor

Drawn with seed `20260807` from 119 distinct-text candidates, capped at 4 messages per vendor. Without the cap the draw came back 61/119 Smart and repeated the `Hi Scott !` personalisation six times — a fingerprint the model could learn instead of the task.

`msg00217 msg00219 msg00262 msg00598 msg00813 msg00814 msg00815 msg00818 msg00851 msg00989 msg01277 msg01287 msg01334 msg01345 msg01385 msg01443 msg01446 msg01466 msg01532 msg01543 msg01821 msg01872`

Vendor mix: UnionBank 4, Maya 4, Smart 4, other 3, SM 2, PLDT 2, GCash 1, NTC 1, gov 1. 16 of 22 carry Taglish markers.

The UnionBank/UnionDigital loan messages (`msg00813`, `msg00814`, `msg00818`, `msg01446`, `msg01532`) are the most valuable rows here: they are **legitimate loan offers with links, urgency, and prize-like framing** — `msg01532` opens "Congratulations! You are ELIGIBLE for UD Loans… Loan up to P390200" — directly against the four link-free loan *scams* added above. That pairing is what forces the model past surface features.

This stratum also closes a brand gap: the current set has no telco at all, only GCash, BDO, UnionBank, Maya, and gov.

---

## Integrity fixes

These are bundled because they change the numbers on their own.

1. **Drop 4 duplicates.** M020, M015, M054, M053 (keeping M001, M008, M049, M051). M049/M054 and M051/M053 resolve to the *same* corpus row — `msg00246` — so they were double-weighted in every metric run to date. True n today is 51, not 55.

2. **Un-truncate 5 rows.** M039, M041, M045, M049, M054 are cut at exactly 400 characters. The KB holds the full text (M049 is really 660). The eval is currently scoring the model on messages that end mid-sentence and never occur in the wild. Re-pull full text from `message_examples`.

3. **Close the M010 retrieval leak.** `msg01484` (`eval_holdout=0, retrievable=1`) is a one-character variant of `msg01483`, which *is* held out and is eval row M010. The Retriever can serve M010's own twin as evidence. This violates pipeline invariant 5. Set `msg01484` to `eval_holdout=1, retrievable=0` and rebuild the KB. The other 52 rows are correctly held out.

4. **Hold out the 34 additions.** Every added row must get `eval_holdout=1, retrievable=0` and the KB rebuilt, or the new messages leak on day one. This is the step most likely to be forgotten.

5. **Fill `notes_for_lui`.** Empty on all 55 rows today. Every row gets one line on why it is hard. That column is the difference between a dataset and a spreadsheet when Lui writes the paper.

6. **Replace `difficulty`.** It is currently a second copy of `gold_label` — every `hard-negative` is LEGIT, every `target-threat`/`scam-other` is SCAM. It carries no information and reads as if the set were stratified by difficulty when it is not. Replace with two honest columns: `has_link` (bool) and `hardness` (`easy`/`hard`), assigned by the curator, not derived from the label.

---

## Harness changes

`backend/eval/run_eval.py` gains one section and one flag.

**Regex baseline row.** Compute the `has_link → SCAM` baseline over the same records and render it in the report immediately above the pipeline metrics. Cheap, zero LLM calls, and it is the control that makes the headline number mean something. Report both, always.

**Link detection is not a regex you can trust.** Writing the baseline surfaced that both the KB's `has_url` column and three successive hand-written detectors disagreed with the truth, and the corpus disagrees with `has_url` on **199/1571 rows (13%)**. Scammers evade detection with digit-only domains (`6384.de/yvJl`), bare IPs (`38.11.89.109`), Cyrillic IDNs (`9910.омск.рус`), brace wrapping (`{ kklfph.fyi }`), and spaced dots (`lizzbf1964@gmail. com`).

Two consequences, and the second is a result worth presenting:

- `has_link` for the eval CSV must be **assigned by hand** during curation, not computed. A buggy detector would silently mis-stratify the set.
- The fragility of link detection is itself an argument for the pipeline. A rule-based filter has to win an arms race on link syntax; an intent-matching model does not. Say this out loud in the write-up — it converts the confound into a motivation.

### Language coverage

`run_eval.py:155` hardcodes `"tl"`, so the `en` path is never evaluated despite `3351e24` having fixed a language-directive bug there. Add `--language {tl,en}` and run `en` over a **fixed 15-message subset**, reported separately. Full dual-language runs cost double for a check that one stratum answers.

---

## KB defects to reconcile

Both are in `knowledge-base/`, which is Nian's to change.

### `click-this-link` prevalence claim is wrong by ~17x

`lure_patterns.click-this-link` states *"Two-thirds of scam messages carry no link at all, so a link is a strong signal but its absence proves nothing."*

Measured against the corpus that ships in the same database: **26 of 692** unheld SCAM messages are link-free — 3.8%, not 67%. The claim and the data cannot both describe the same population. It is presumably a cited external figure that was never checked against the corpus. Either attribute it to its source and note the corpus disagrees, or replace it with the measured figure. Leaving it as-is puts a refutable claim in the KB the Advisor reads from.

The rhetorical guidance ("its absence proves nothing") stays correct either way and should survive the edit.

### Label noise in the corpus

Of the 26 link-free SCAM messages, **10 are unusable** — a 38% defect rate in that slice:

| id | text | problem |
|---|---|---|
| `msg01066` | "You will no longer receive marketing SMS from BPI. Thank you." | Legit opt-out confirmation, labelled SCAM |
| `msg00638` | "Welcome to CMHK! Calling home / other countries? Dial…" | Legit roaming welcome, labelled SCAM |
| `msg00168` | Torre Lorenzo condo presentation invite | Aggressive marketing; SCAM is defensible but disputed |
| `msg00167` | "Hello" | Fragment, unlabelable |
| `msg00516` | "Hi po" | Fragment |
| `msg00887` | "001204649" | Fragment |
| `msg01463` | "getcash!!" | Fragment |
| `msg01770` | "eccash-loan now" | Fragment |
| `msg01369` | "Nakuha mo ung pera?" | 19 chars; plausibly a money-mule probe but too short to label |
| `msg01010` | "0943 135 1863 0917 869 9250 0917 847 1553" | Bare phone numbers, no message |

Gold labels are inherited from the upstream Kaggle dataset. **We have not been measuring against clean ground truth.** This slice is small and hand-checkable; the other ~1,545 rows are not, and this spec does not claim they are clean. The honest move for the paper is to state the sampling method for the eval set (hand-reviewed) and note the retrieval corpus is inherited unreviewed.

Fragments should be dropped from `retrievable` regardless — a 9-character "getcash!!" chunk is retrieval noise whatever its label.

---

## Verification

1. `n == 85`; no two rows share normalised text.
2. No row's text is exactly 400 characters (the truncation fingerprint).
3. Every eval row's text matches a `message_examples` row with `eval_holdout=1, retrievable=0`; zero rows with `retrievable=1`. This is the invariant-5 check and it must run in CI, not by hand — it is how M010 got through.
4. `kb_chunks` contains no chunk whose `parent_id` is a held-out message.
5. Regex baseline over the new set lands within ±0.05 of **F1 0.660** (measured as built). A materially higher figure means the composition drifted.
6. `chunk_count` in `/api/meta` reflects the rebuilt KB. The 732 figure in `CLAUDE.md` changes once rows move to held-out — **update the deploy runbook's expected count in the same commit**, or the next redeploy verification will report a false failure.
7. `cd backend && uv run pytest` passes.

## Docs to update in the same commit

| File | Change |
|---|---|
| `qa/TEST-PLAN.md` | New eval composition, the regex-baseline control, hand-assigned `has_link` |
| `docs/PRD.md` | Email/bare-URL eval coverage as a stated limitation; success criteria restated against the new set |
| `CLAUDE.md` | Expected `chunk_count` for the deploy check; invariant 5 gains the CI assertion |
| `docs/ARCHITECTURE.md` | Only if `run_eval.py`'s report contract is treated as an interface |
| `knowledge-base/README.md` | Holdout count, the `click-this-link` correction, the label-noise caveat |

## Decisions taken

**Filename.** `eval-set-candidate-55.csv` → **`eval-set.csv`**. The old name encoded a size that becomes wrong at n=85, and would become wrong again at the next revision. Rename with `git mv` to keep history.

Eleven files reference the old name. They split three ways:

| Files | Action |
|---|---|
| `backend/eval/run_eval.py`, `knowledge-base/scripts/build_kb.py`, `knowledge-base/scripts/verify_kb.py`, `backend/tests/fixtures/make_fixture.py` | **Code — must update.** `build_kb.py` and `verify_kb.py` read this file to decide what to hold out, so a missed reference breaks the holdout, not just a docstring. |
| `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/GUIDE.md`, `qa/TEST-PLAN.md` | **Live docs — update.** |
| `docs/superpowers/specs/2026-08-05-scam-shield-knowledge-base-design.md`, `docs/superpowers/plans/2026-08-06-scam-shield-knowledge-base.md` | **Historical — leave alone.** These record what the file was called when they were written, the same reasoning `CLAUDE.md` applies to pre-rename "Elderly Scam Shield" references. |

**`chunk_count` expectation.** Moving 34 rows to held-out drops the count below 732. `CLAUDE.md`'s redeploy runbook hard-codes 732 as the pass condition for `/api/meta`, so it must be updated in the same commit or the next deploy verification reports a false failure. Read the rebuilt value from the KB rather than predicting it.
