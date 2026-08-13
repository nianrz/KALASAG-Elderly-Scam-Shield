---
title: "Knowledge base + RAG — 2-minute script and 3-slide outline"
type: note
term: AY2526-T3
subject: STSP001-Industry-Invited-Lectures
owner: Nian (Domain)
updated: 2026-08-13
tags: [capstone, kalasag, presentation, script, slides, knowledge-base, rag]
---

# Knowledge base + RAG — 2-minute script and 3-slide outline

**For:** whoever presents the data and retrieval section.
**Source of truth for every number here:** `docs/2026-08-13-kb-and-rag-in-plain-language.md`
and `knowledge-base/out/build_report.json`. If a figure ever disagrees, the build
report wins.

## Timing

| Slide | Topic | Target | Word count |
|---|---|---|---|
| 1 | Where the data came from | 0:00 – 0:42 | 108 |
| 2 | What's in it, and what we hide | 0:42 – 1:24 | 106 |
| 3 | What the search searches over | 1:24 – 2:20 | 140 |

Total ≈ **354 words ≈ 2:22** at a comfortable 150 words per minute. If you speak
fast, you'll land at 2:05. Trims to get back under 2:00 are at the bottom.

## ⚠ Known cost of the current slide 3

Slide 3 now shows the **composition of the knowledge base**, which is the same
subject as slide 2. Two consequences, both manageable but worth knowing:

1. **Slides 2 and 3 overlap.** Slide 2 shows 1,571 → 569 and the four content
   types; slide 3 re-cuts the same material. The scripts below are written to
   avoid saying anything twice — slide 2 owns the *filtering*, slide 3 owns the
   *mix*. Keep that division or the repetition will be audible.
2. **The RAG mechanism has no slide.** Redaction, the Taglish → English concept
   hop, and the keyed hotline lookup are now spoken-only. The script below
   carries all three. Do not cut them; they are the only place the pipeline gets
   explained at all.

## ⚠ Never label the advisory row `BSP/NBI/DTI/telco`

An earlier version of this table captioned the 26 advisory chunks as
`scraped BSP/NBI/DTI/telco advisories`. That is wrong three ways and contradicts
slide 1.

- **BSP is not a source.** It is the one fetch that failed, and slide 1 says you
  deleted their hotline because of it.
- **NBI and DTI are not sources.** They never were.
- The actual 9: BDO, GCash, Maya, UnionBank, NPC, NTC, PNP-ACG,
  ScamWatch Pilipinas, cybersecurity.ph.

Correct caption: **`official advisories — banks, e-wallets, PNP-ACG, NTC, NPC`**
Verify against `knowledge-base/ATTRIBUTION.md`, generated from the `sources`
table on every build.

---

# SLIDE 1 — Built from sources we can point at

## What goes on the slide

**Title:** Where the knowledge base came from

**Two columns:**

| Real scam messages | Official counter-advice |
|---|---|
| Public PH research dataset | Fetched from the publishers themselves |
| One Filipino's inbox, several years | GCash · BDO · UnionBank · Maya |
| CC BY 4.0 — free to use with credit | PNP-ACG · NTC · NPC · ScamWatch PH |
| 8,255 messages → 1,571 usable | 9 advisories, each saved with its date |

**Callout box, bottom (make this visually prominent):**

> **BSP's website was down every time we tried.**
> We deleted their hotline instead of typing it from memory.

**Footer strip:** `4 fetched by script · 5 needed a browser · 1 failed — all logged`

## Speaker script

> Our knowledge base comes from two kinds of sources, collected two different
> ways.
>
> The scam examples are real Filipino text messages — one person's inbox over
> several years, published as a public research dataset under a licence that
> lets us use it as long as we credit the author.
>
> The counter-advice comes straight from the organisations that published it:
> GCash, BDO, UnionBank, Maya, the PNP Anti-Cybercrime Group, the NTC. Every
> quote and every hotline in our database was copied from a page we actually
> visited, with the date recorded. Nothing was typed from memory.
>
> When the Bangko Sentral's site was down every single time we tried it, we
> removed their hotline rather than ship a number we couldn't point to a source
> for.

## Delivery notes

- **Land the BSP line.** Pause before it. It's the strongest thing you say in the
  whole two minutes — it proves the discipline is real and not a claim.
- Don't read the two columns aloud. The slide shows them; you narrate over them.
- If someone looks skeptical about "nothing was typed from memory": our build
  script **refuses to finish** if any served row cites a source without a date.

---

# SLIDE 2 — Curated, not dumped

## What goes on the slide

**Title:** What's inside — and what we deliberately hide

**Top row, four stat tiles:**

| 1,571 | 9 | 10 | 4 + 4 |
|---|---|---|---|
| real messages | official advisories | named scam tactics | brand denials + hotlines |

**Middle — the funnel (the visual centrepiece):**

```
1,571 messages  →  569 searchable
```

| We hide | Rows | Why |
|---|---|---|
| Legitimate messages | 844 | Our library is evidence of *scams* |
| Our test set | 88 | So it can't look up its own exam answers |
| Fragments under 20 characters | 6 | "Hello", "getcash!!" — no pattern to match |
| Near-identical copies | 106 | Same scam, one number changed |

**Bottom banner — the measured result:**

> **Evidence per query: 5.4 → 6.0 distinct messages** (worst case 2 → 6)
> Type-correct recall@6: **0.800 → 0.829**

**Small print:** `Nothing is deleted — hidden rows stay in the database, auditable`

## Speaker script

> Here's what's inside: 1,571 real messages, 9 official advisories, 10 named
> scam tactics, and 4 brands' own denials with their real hotlines — all in one
> SQL database.
>
> But we only let the system search 569 of those messages.
>
> We hide the legitimate ones, because our library is evidence of scams. We hide
> our 88 test messages, so the system can't look up the answers to its own exam.
> And we found 106 near-identical copies — the same scam re-sent with one number
> changed — and hid those too.
>
> That last filter is our measured win. The evidence the AI sees per query went
> from 5.4 genuinely different messages to a full six.

## Delivery notes

- **"569 of 1,571" is the hook.** Say it slowly. Hiding two-thirds of your own
  data on purpose is the thing that reads as curation rather than dumping.
- The dedup number is the **only claim in this deck with a measured before and
  after.** Say "measured" out loud.
- If you have a spare beat: *"in the worst case, four of the six pieces of
  evidence used to be copies of each other."*
- **Do not** claim this improved final verdict accuracy. It hasn't been measured.

---

# SLIDE 3 — RAG System

## What goes on the slide

**Title:** RAG System
**Subtitle (add this — it's the only thing missing):** `609 searchable pieces`

Four cards, 2 × 2, same layout you already have. Each card is a **big number**
plus a **three-word label**:

| Card | Number | Label |
|---|---|---|
| 1 | **569** | Real scam texts |
| 2 | **26** | Official advisories |
| 3 | **10** | Named scam tactics |
| 4 | **4** | Brands' own denials |

### Suggested edits, and why

**Replace the raw table names.** `message_example`, `lure_pattern`, and
`brand_rebuttal` are database identifiers, not audience language. The labels
above are the same four things in words a panelist reads without decoding. This
*removes* characters — it is not more text.

**Add the numbers.** Without them the four cards are a list; with them they are
an argument. The counts are the entire reason this slide exists.

**Add the `609` subtitle.** It is what the four cards sum to, and without it
nobody knows whether the library is big or tiny.

**Keep the filter sentence off the slide.** "Only 569 of 1,571 corpus messages
are retrievable…" is a full paragraph, and the filtering is slide 2's job. Say
it, don't display it.

**Optional, costs text:** the schema name in small type under each label, if you
want the technical flavour visible. Skip it unless the panel is technical.

**Do not add a "what it is" description column.** It doubles the text on the
slide to say what you are about to say out loud anyway.

## Speaker script

> RAG just means open-book instead of closed-book. Before the AI answers, we go
> find the six most relevant entries in our library and put them in front of it.
> **This is that library** — 609 pieces of text, and deliberately not all the
> same kind of thing.
>
> 569 are real scam texts. 26 are sections of official advisories. 10 are scam
> tactics we named and described ourselves. 4 are the brands' own denials, in
> their own words.
>
> **The mix is the point.** One search can come back with five real scam texts
> *and* one BDO statement saying they never send links — so the AI sees the
> pattern and the official rebuttal in the same handful.
>
> Before any of that, we strip the user's OTPs, account numbers, and phone
> numbers, and we translate the message into English red-flag concepts, because
> our library is English and our users write Taglish.
>
> And one thing is never searched at all: **the hotline.** That's looked up
> exactly, by ID, like a phonebook. A similarity match is about ninety percent
> right — and for a phone number handed to a frightened seventy-year-old, ninety
> percent right is wrong.

## Delivery notes

- **"This is that library" is the load-bearing sentence.** Four cards of numbers
  mean nothing until you say what they are numbers *of*. Say it, then pause, then
  point.
- **Never say "retrieval-augmented generation"** unless a panelist says it
  first. Open with the open-book line every time.
- **The mix is the argument, not the total.** Anyone can put 609 rows in a
  database. The defensible choice is that curated content — advisories, named
  tactics, brand denials — sits in the same searchable pool as the raw scam
  texts, so a single search returns the pattern *and* the rebuttal. If only one
  point lands, make it that one.
- **Do not read the four cards aloud as a list.** The slide shows them. You are
  supplying what the mix buys you.
- **Paragraph four is doing double duty.** Redaction and the Taglish → English
  hop have no slide any more, so this is their only appearance in the whole
  deck. It is compressed on purpose. Do not cut it, and do not expand it either —
  if a panelist wants more, that is what Q&A is for.
- **Do not repeat slide 2's filtering numbers here.** Slide 2 owns 1,571 → 569.
  Slide 3 owns the mix. Saying both twice is the fastest way to sound padded.
- **Land the phonebook line and stop.** "Ninety percent right is wrong" is the
  last thing they should hear from this section — don't tail off into a summary.
- If asked to elaborate on the hotline: the file that does that lookup literally
  opens with the comment *"No similarity search, ever."*
- If asked why 26 advisory chunks from only 9 documents: we split long advisories
  at paragraph boundaries, so a search returns the relevant section rather than a
  whole page.

---

# If you're running long

Cut in this order. Each cut is clean — nothing downstream depends on it.

1. **Slide 1** — drop `Maya` and `NPC` from the spoken list. Say "GCash, BDO,
   UnionBank, the PNP Anti-Cybercrime Group, and the NTC." *(−4 seconds)*
2. **Slide 2** — drop the fragments filter from the script. It's 6 rows and the
   slide already shows it. *(−6 seconds)*
3. **Slide 3** — shorten the mix example to *"five real scam texts and one BDO
   statement."* *(−5 seconds)*
4. **Slide 3** — cut *"and 4 are the brands' own denials, in their own words"* to
   *"and 4 are the brands' own denials."* *(−4 seconds)*
5. **Slide 3** — in paragraph four, drop *"account numbers, and phone numbers"*
   and say only *"we strip the user's private details."* *(−5 seconds)*

All three together bring the talk back under 2:05.

**Never cut:** the BSP line, "569 of 1,571," "this is that library," or the
phonebook contrast. Those are the four things worth remembering.

**Never cut paragraph four of slide 3.** Redaction and the Taglish → English hop
appear on no slide at all. Shorten it if you must; deleting it means the pipeline
never gets described.

---

# If you're running short (you have ~20 seconds spare)

Add exactly one of these, not more:

- **On slide 2:** *"And this measurement actually killed our own earlier plan —
  we'd been considering cutting the retrieval window from six down to three,
  because slots four to six looked like they were adding nothing. Once the
  duplicates were gone, they started earning their place. We dropped the plan."*
- **On slide 3:** *"The concepts cross the language gap and describe the tactic;
  we search with the original text alongside them, because that's what catches a
  specific brand or link a paraphrase would lose."*

---

# Q&A landmines — one-line answers

Have these ready. Do not volunteer them.

**"Did retrieval actually change the verdict?"**
> Not measured yet, and I want to be precise about that. End-to-end accuracy
> structurally can't tell "fetched garbage and guessed right" from "fetched good
> evidence and used it." The test that separates them is an ablation — run the
> evaluation twice, once with retrieval off. That's about 680 model calls and
> it's our next run.

**"How do you know your labels are correct?"**
> Our 85 evaluation messages are hand-reviewed. The rest of the corpus inherits
> its labels from the original dataset and we did not re-derive them — in one
> 26-message slice we checked by hand, 10 were unusable. We say that in the
> paper rather than presenting inherited labels as verified ground truth.

**"Couldn't a simpler method do this?"**
> Similarity alone, with no AI at all, reaches 0.824 accuracy on our data. That's
> the floor our pipeline has to beat, and we track it deliberately for exactly
> that reason.

**"Is your data representative of Philippine scams generally?"**
> No, and we don't claim it is. It's one person's inbox, and it skews heavily
> toward online casino spam — 420 of 727 scam messages. It's real Philippine
> data, which is more than a generic phishing dataset gives us, but it's one
> sample.

**"Why not just fine-tune a model?"**
> Costs money, needs a large labelled dataset we don't have, and has to be redone
> every time we change models. Updating our knowledge base means editing a text
> file and re-running a script — which matters when the domain expert on the team
> is a student, not an ML engineer.

---

# Print card — the whole script, uninterrupted

Tape this to your notes.

> Our knowledge base comes from two kinds of sources, collected two different
> ways. The scam examples are real Filipino text messages — one person's inbox
> over several years, published as a public research dataset under a licence
> that lets us use it as long as we credit the author. The counter-advice comes
> straight from the organisations that published it: GCash, BDO, UnionBank,
> Maya, the PNP Anti-Cybercrime Group, the NTC. Every quote and every hotline in
> our database was copied from a page we actually visited, with the date
> recorded. Nothing was typed from memory. When the Bangko Sentral's site was
> down every single time we tried it, we removed their hotline rather than ship
> a number we couldn't point to a source for.
>
> Here's what's inside: 1,571 real messages, 9 official advisories, 10 named
> scam tactics, and 4 brands' own denials with their real hotlines — all in one
> SQL database. But we only let the system search 569 of those messages. We hide
> the legitimate ones, because our library is evidence of scams. We hide our 88
> test messages, so the system can't look up the answers to its own exam. And we
> found 106 near-identical copies — the same scam re-sent with one number
> changed — and hid those too. That last filter is our measured win. The evidence
> the AI sees per query went from 5.4 genuinely different messages to a full six.
>
> RAG just means open-book instead of closed-book. Before the AI answers, we go
> find the six most relevant entries in our library and put them in front of it.
> This is that library — 609 pieces of text, and deliberately not all the same
> kind of thing. 569 are real scam texts. 26 are sections of official advisories.
> 10 are scam tactics we named and described ourselves. 4 are the brands' own
> denials, in their own words. The mix is the point. One search can come back
> with five real scam texts and one BDO statement saying they never send links —
> so the AI sees the pattern and the official rebuttal in the same handful.
> Before any of that, we strip the user's OTPs, account numbers, and phone
> numbers, and we translate the message into English red-flag concepts, because
> our library is English and our users write Taglish. And one thing is never
> searched at all: the hotline. That's looked up exactly, by ID, like a
> phonebook. A similarity match is about ninety percent right — and for a phone
> number handed to a frightened seventy-year-old, ninety percent right is wrong.
