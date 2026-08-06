# PRD — Kalasag

**Status:** approved 2026-08-06 · **Deadline:** presentation in one week · **Owner:** Aki (Lead)

## Name

**Kalasag**, renamed from "Elderly Scam Shield" on 2026-08-06. Full form for titles and the deck: *Kalasag — Elderly Scam Shield*. In the product itself it is just **Kalasag**.

*Kalasag* is the hardwood shield carried by pre-colonial and indigenous Filipino warriors, paired with the kampilan and the spear. Three reasons it fits better than a literal English descriptor:

- **It is defensive, not adversarial.** A shield describes what the product does — absorb an incoming attack — without promising to defeat the attacker. That matches a product whose core invariant is that it never claims certainty.
- **It appears on the seal of the Philippine National Police**, the agency the app routes users to through PNP-ACG. The name and the next step point at the same symbol.
- **It is Filipino, for Filipino users**, in a product whose whole premise is that existing advice is English-only and generic.

One caveat to state if asked: **Gawad KALASAG** is an existing national award for disaster-resilience work, run under the NDRRMC. Different domain and a different kind of thing, so confusion is unlikely, but we should be the ones to raise it rather than let a panelist find it. We are not affiliated with it and the deck should not imply otherwise.

## Problem

Filipino scam SMS is high-volume and well-targeted. In the 8,255-message corpus the team analysed, 827 messages are outright scams, and the largest categories — online casino promos and bank impersonation — are written in Taglish that reads as ordinary to someone unfamiliar with the pattern. Elderly users are the least equipped to distinguish them and the least able to recover from a loss.

Existing advice is generic ("don't click suspicious links") and English-only. Nothing tells a specific person whether the specific message in their hand is a scam, in a language and register they read comfortably.

## Users

**Primary — the elderly recipient.** Receives the message, pastes it, wants a plain answer. Low tech confidence. May be reading on a small screen with reduced vision. Panics easily under urgency framing, which is exactly what the scam exploits.

**Secondary — the family caregiver.** Screening on someone else's behalf, often remotely. Comfortable in English. Wants enough detail to explain the verdict to the person who received it.

The `English | Tagalog` toggle exists because these two users want different output languages. It is set before the message is submitted; the analysis is produced in the language chosen at that moment and cannot be re-languaged afterwards without paying for a second run.

## Goals

1. **Identify** whether a message is a scam and name its pattern.
2. **Explain** the verdict in plain Filipino/Taglish, naming the specific red flags in this message.
3. **Recommend next steps** — don't click, block, verify via the official hotline, report to I-ARC 1326 / PNP-ACG.
4. Ship a **running multi-agent (LangGraph) prototype** over a curated knowledge base.
5. Document **guardrails and failure modes**, with a measured accuracy figure.

## Scope

**In**
- Paste-in text: SMS, email body, or URL. Filipino, English, or Taglish.
- Verdict → explanation → next steps output.
- LangGraph `retrieve → detect → advise` pipeline with a confidence-gated self-reflection loop.
- Curated Philippine scam knowledge base (Nian's deliverable).
- `English | Tagalog` output toggle.
- Elderly-accessible UI.
- Evaluation over the 55-message gold-labelled set, with a calibrated confidence threshold.
- Guardrail and failure-mode documentation.

**Out this term**
- Screenshot / OCR input — **future work**, presented not built (see Limitations).
- Voice input and text-to-speech.
- Telco or network-level integration.
- Live threat feeds.
- Public deployment. The demo runs locally.
- Languages beyond Filipino / English / Taglish.
- Accounts, history, persistence of user submissions.

## Requirements

### Functional

| # | Requirement |
|---|---|
| F1 | User pastes text into a single input and submits. |
| F2 | Preprocessing detects message type (SMS / email / URL) and redacts PII before any LLM call. |
| F3 | The RAG Agent rewrites the message into English red-flag concepts, then retrieves matching KB chunks by vector similarity. |
| F4 | The Detector emits a verdict, a confidence score, and the specific red flags found, citing retrieved chunks. |
| F5 | Below the confidence threshold, the Detector re-runs once with a self-reflection prompt stating why the prior pass was low-confidence. |
| F6 | The Advisor produces an explanation and concrete next steps in the selected language. |
| F7 | Hotlines and official URLs are looked up by key and passed to the Advisor as data, never generated. |
| F8 | The UI toggles static copy between English and Tagalog without re-running the analysis, and the choice sets the language the analysis is produced in. The toggle is hidden on the result screen, where model-written text can no longer follow it — see `DESIGN.md § Language is chosen before the analysis`. |
| F9 | The UI shows the KB freshness date. |
| F10 | The UI shows similar known scams from the corpus. |

### Non-functional

| # | Requirement |
|---|---|
| N1 | End-to-end response under 30 seconds on a typical message. |
| N2 | Body text at least 18px, contrast at least 4.5:1, tap targets at least 44px, no timeouts. |
| N3 | Raw user input is never written to logs, disk, or graph state. |
| N4 | Switching LLM provider is an env-var change and requires no re-embedding. |
| N5 | The app runs offline apart from the LLM API call. |
| N6 | The E2E suite runs without a provider key or network access. Only the smoke spec needs either. |
| N7 | The project incurs no LLM API cost. It runs on free tiers and the Accenture Bedrock sandbox. |

### Verdicts

`SCAM` · `LIKELY_SCAM` · `UNCLEAR` · `LIKELY_LEGIT`

There is no `SAFE`. Every verdict renders with a verify-independently line. This is a guardrail, not a UI preference.

## Success criteria

| # | Criterion | How it is verified |
|---|---|---|
| S1 | Any pasted message produces a verdict, an explanation naming at least one red flag, and at least one next step. | Manual run on 10 unseen messages. |
| S2 | Accuracy, precision, and recall are measured on all 55 gold-labelled messages. | `eval/run_eval.py` output. |
| S3 | The confidence threshold is chosen from measured data, not asserted. | Threshold sweep table in the eval output. |
| S4 | The self-reflection loop fires on low confidence and fires at most once. | Unit test with a fake LLM. |
| S5 | No eval-set message is retrievable from the KB. | Verification gate in the KB build. |
| S6 | A native speaker judges the Tagalog output as plain Taglish rather than formal Tagalog. | Team review on 10 outputs. |
| S7 | Switching `LLM_MODEL` between two providers requires no code change. | Run the demo on both. |
| S8 | Every user-facing state in `DESIGN.md` — four verdicts, both languages, and every error path — is covered by an automated E2E spec. | `npm run e2e` green in `qa/`. |
| S9 | The accessibility rules in N2 are asserted automatically, not eyeballed. | `qa/cypress/e2e/a11y/accessibility.cy.ts`. |
| S10 | The frontend and the API agree on the response contract. | `npm run e2e:smoke` against the live backend. |

## Limitations

Stated on the deck, not hidden.

- Cannot catch every novel or adversarial scam. The KB freshness date is shown in the UI.
- False positives and negatives are inherent. The threshold trades one against the other; the eval reports both.
- **Confidence is self-reported by the model and is a known-imperfect proxy.** The threshold is calibrated on our own eval set, so the reported accuracy is not held-out accuracy. We report it as such.
- Users may paste OTPs or account numbers. These are redacted before the LLM call and never logged, but the risk is real.
- **Cross-lingual retrieval is a known weak point.** Authoritative sources are English; scam messages are Taglish. Mitigated two ways: a multilingual embedding model, and the RAG Agent extracting English concepts before retrieval.
- **The input method is itself a risk.** Long-pressing a scam SMS to copy it can accidentally open the link — the exact outcome the product prevents, in the population least able to recover. Screenshot/OCR input is the designed mitigation and is presented as future work, not shipped.
- Near-duplicate scam messages that are neither identical nor prefixes of eval-set entries remain retrievable. The corpus is heavily templated, so this weakens the eval slightly.
- **A finished result cannot be re-languaged.** The language is fixed at submit time; reading the same verdict in the other language means running it again. Caching the Advisor's output per language was not worth the change a week from the demo.

## Open questions

| # | Question | Status |
|---|---|---|
| 1 | Is a deployed demo required by the course? | Course-side, unresolved. We demo locally. |
| 2 | Which models does the Accenture Bedrock sandbox expose? | **Answered 2026-08-06.** Claude models via bearer-token auth; Claude Sonnet 5 works from ap-southeast-1 through the global inference profile and is now the default and only provider. Gemini support and its free-tier key were removed the same day. |
| 3 | Does screenshot/OCR input ship in a later term? | Deferred deliberately. |

## Future work

Voice and text-to-speech for low-vision users · screenshot/OCR input · telco adoption as a B2B channel · continuously-updated threat feed · broader language coverage.
