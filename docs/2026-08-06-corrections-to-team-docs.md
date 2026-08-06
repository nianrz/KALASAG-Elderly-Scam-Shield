---
title: "Corrections to team docs — from KB build"
type: note
term: AY2526-T3
subject: STSP001-Industry-Invited-Lectures
updated: 2026-08-06
tags: [capstone, elderly-scam-shield, knowledge-base, corrections]
---

# Corrections to team docs — from the KB build

**From:** Nian · **For:** Aki, James, Lui
**Source of truth:** `knowledge-base/out/build_report.json`, built 2026-08-06,
with all 8 integrity gates passing.

The canonical topic page and the deck live in the Obsidian vault, outside the
KB repo, so these are stated as apply-directly edits rather than made for you.
Five corrections. Two of them are claims a mentor can disprove in ten seconds,
so please do 1 and 3 even if you skip the rest.

---

## 1. `topics/capstone-elderly-scam-shield.md`, Knowledge Base section

**Current text:** "Licence and label quality unverified"

**Replace with:** "Licence verified: CC BY 4.0 (Scott Lee Chua, PH Spam and
Marketing SMS). 8,255 messages, of which 1,907 have usable text after the
author's privacy redaction — spam 827, ads 933, gov 144, notifs 3, OTP 0.
Coverage runs to 2026-06-03."

**Why:** It was verified on 2026-07-29 and re-verified against a fresh pull on
2026-08-06; the build reconciles every category count to the expected figures
with all deltas at zero. Leaving "unverified" on the page understates work
that is done and invites the one question we can already answer completely.

---

## 2. `topics/capstone-elderly-scam-shield.md`, same section — the taxonomy

**Current text:** the scam taxonomy "phishing / smishing / vishing / romance /
OFW / investment / package-delivery"

**Replace with** the measured taxonomy now in `lure_patterns`, ordered by
measured count against the 827-message spam corpus:

| Pattern | Type | Count | Share |
|---|---|---|---|
| Online casino or gambling promotion | casino | 465 | 56.2% |
| Verify or update your account | bank-impersonation | 44 | 34% of its slice |
| Account suspended or restricted | bank-impersonation | 31 | 24% of its slice |
| Urgency deadline | bank-impersonation | 22 | 17% of its slice |
| Click this link | bank-impersonation | 22 | 17% of its slice |
| Job or task scam | job-task | 21 | 2.5% |
| Unsolicited loan offer | loan | 16 | 1.9% |
| Package or delivery problem | package | 14 | 1.7% |
| Prize or raffle win | prize | 14 | 1.7% |
| Crypto or investment offer | crypto | 3 | 0.4% |

**Why:** the old taxonomy is disproved by the corpus. Four of its seven
categories are near-absent in SMS; **vishing is inapplicable outright because
the product accepts no audio**; and the two largest real categories —
gambling/casino and bank/e-wallet impersonation — do not appear in it at all.
We would be presenting a taxonomy we assumed over one we measured.

**Known reconciliation gap, please read before quoting these numbers.** The
counts in that table are the 2026-07-29 hand-analysis figures, carried into
`lure_patterns` as-is. The keyword lists that produced them were never
recorded, so `kb/tagging.py` is a reconstruction, and on the same 827-message
spam corpus it computes somewhat different figures: casino 481 (58.2%),
bank-impersonation 76 (9.2%), prize 23, loan 10, package 10, crypto 2,
job-task 2, and **223 (27.0%) matching no list at all**. The direction and the
headline are unchanged — casino dominates at roughly 56–58%, bank impersonation
is second — but do not present the two sets of numbers as if they came from one
method. If asked, the honest answer is: the ranking is robust, the exact counts
depend on the keyword list, and the unclassified 27% is the real coverage gap.

---

## 3. Deck slide 7, line 100

**Current text:** "No public labeled Filipino/Taglish scam dataset exists
(pending Nian's dataset research confirmation)"

**Replace with** the dataset-research-done paragraph from
`2026-07-29-nian-dataset-findings.md`.

**Why:** it is false, it is disprovable in ten seconds by anyone with a search
bar, and the parenthetical advertises that we did not check. The dataset is
public, licensed CC BY 4.0, and the whole knowledge base is built on it. This
is the single most damaging line in the deck.

---

## 4. Deck slide 6

**Replace wholesale** with `2026-08-06-kb-summary-for-slide6.md`.

**Why:** the KB now exists as a built, gated artefact. Slide 6 should report
what it contains, not what it will contain.

---

## 5. Scope correction — the brand list

**Anywhere the five brands "BPI, BDO, GCash, Maya, Metrobank" are listed**
(June scope), replace with the four the KB actually curates: **GCash, BDO,
UnionBank, Maya.**

**Why:** measured impersonation frequency in the corpus, against a scope
chosen before anyone counted:

| Brand | In scope? | Measured SCAM messages |
|---|---|---|
| GCash | yes | 34 |
| BDO | yes | 30 |
| **UnionBank** | **no — was absent from the scope** | **27** |
| Maya | yes | 6 |
| BPI | yes | 1 |
| Metrobank | yes | 0 |

UnionBank is the #3 brand and was not on the list at all. BPI has one message
and Metrobank has none — we scoped two brands the data does not support and
missed one it does.

**Note the change from the 2026-07-29 numbers.** The July figures were
GCash 39 / UnionBank 29 / BDO 24 / Maya 9. The keyword lists behind them were
never recorded, so `kb/tagging.py` is a reconstruction and its counts differ.
The rule we are holding to is to report computed counts and never tune the
lists until they reproduce old numbers. **One conclusion changes: BDO, not
UnionBank, is the measured #2 brand.** If a slide or script says "UnionBank is
#2", it needs to say #3 — the more interesting point (a top-3 brand was missing
from our scope entirely) survives intact.

---

## Not a correction, but worth knowing

The BSP consumer-assistance hotline that was in an earlier draft of the
reporting contacts has been **removed**. `bsp.gov.ph` has served a genuine
"Website is undergoing maintenance" notice on every fetch across three rounds,
so the number could not be sourced from BSP itself. We are not handing an
elderly user a phone number on no authority but memory. Four verified contacts
remain, led by I-ARC 1326.
