---
title: "The knowledge base and RAG, in plain language"
type: note
term: AY2526-T3
subject: STSP001-Industry-Invited-Lectures
owner: Nian (Domain)
updated: 2026-08-13
tags: [capstone, kalasag, knowledge-base, rag, retrieval, presentation, explainer]
---

# The knowledge base and RAG, in plain language

**Who this is for:** whoever presents the data and retrieval section, and anyone
who has to answer a panelist without hedging.

**What this is:** the five questions people actually ask about our data, answered
twice — once in plain language you can say out loud, once with the technical
detail and the file that backs it.

**Companions.** `docs/rag-explained.md` is the mechanism in depth.
`docs/2026-08-10-rag-use-and-optimization.md` is what we optimized and what the
evidence is. `knowledge-base/README.md` is the build figures and the caveats.
If any of those disagrees with this document, **they win** — this one is the
translation, not the record.

---

## The one-paragraph version

> Kalasag doesn't guess from what an AI happens to remember. We built a
> Philippine scam library — 1,571 real Filipino text messages plus the official
> warnings that GCash, BDO, UnionBank, Maya, the PNP, and the NTC published
> themselves. When you paste a suspicious message, the system finds the six most
> similar things in that library and hands them to the AI as evidence before it
> gives a verdict. The hotline numbers are *not* found by similarity — those are
> looked up exactly, like a phonebook, because a nearly-correct phone number
> given to a frightened lolo or lola is worse than no number at all.

---

# 1. How was the data collected?

## Say it like this

> We collected from two places, in two different ways, because they need
> different levels of trust.
>
> The scam messages came from a **public research dataset** — one Filipino's
> real inbox, collected over several years and published for free under a
> licence that lets us use it as long as we credit the author. We download it
> once, and every time we rebuild our database we re-count it and check the
> numbers still match. If even one count is off, the build tells us instead of
> quietly moving on.
>
> The official warnings and hotlines came **straight from the organisations
> themselves** — we visited GCash's help page, BDO's anti-scam page, the PNP
> Anti-Cybercrime Group's advisories, and so on, and saved a copy of each page
> with the date we got it. Nothing in our database was typed from memory. If we
> couldn't find a real published page for something, we left it out.

## The line that wins the room

> The Bangko Sentral's website was down for maintenance every single time we
> tried it. So we deleted the BSP hotline from our database rather than ship a
> phone number we couldn't point to a source for. Our build script actually
> **refuses to finish** if any served row cites a source we don't have a date
> for.

That one's worth saying unprompted. It's the clearest proof the data discipline
is real and not decorative.

## The technical detail

| | Scam message corpus | Official advisories |
|---|---|---|
| **Where** | `scottleechua/data` on GitHub, `spam-and-marketing-sms/text-messages.csv` | 9 live websites listed in `content/sources.yaml` |
| **Licence** | CC BY 4.0 — attribution required | Public / brand advisory |
| **How** | `kb/dataset.py` — one HTTPS download, cached, never re-downloaded | `scripts/fetch_sources.py` — GET, strip nav/scripts/footers with BeautifulSoup, save the body as markdown with the URL and date in front-matter |
| **Verification** | `reconcile()` re-counts every category on every build and reports deltas | `content/fetch_log.json` records every attempt, including failures |

**Fetch reality, recorded honestly:** 4 sources fetched by script, **5 needed
browser automation** (GCash, UnionBank, PNP-ACG, NTC sit behind Cloudflare and
return 403 to a script — logged as `ok-browser`, and they will *not* reproduce
from `fetch_sources.py` alone), **1 failed** (BSP).

The fetched markdown is committed to the repo, so a rebuild next month doesn't
depend on those sites still being reachable.

---

# 2. What data was collected?

## Say it like this

> Seven tables in one database file. Think of it as a small library with seven
> shelves:
>
> - **Where everything came from** — 10 sources, each with its web address, the
>   date we fetched it, and its licence.
> - **The scam messages** — 1,571 real Filipino texts, each labelled scam or
>   legitimate and tagged by what kind of scam it is and which brand it pretends
>   to be.
> - **The official warnings** — 9 full advisory documents from banks, e-wallets,
>   and government agencies.
> - **The named tricks** — 10 recurring scam tactics, with how often each one
>   actually appears in our messages, and the trigger phrases in both English
>   and Tagalog.
> - **The brands' own denials** — 4 companies' exact published sentences saying
>   "we will never text you a link," plus their real hotline.
> - **Where to report** — 4 organisations in the order a victim should actually
>   contact them.
> - **The searchable version** — 609 pieces of text, which is everything above
>   flattened into one searchable pile.

## The numbers, and what each one means

| Number | Plain meaning |
|---|---|
| **8,255** | Every message in the original dataset |
| **1,907** | The ones we could actually use — the rest had their content blanked out by the original author to protect private data like OTPs |
| **1,571** | What's left after we merge exact duplicates |
| **727** | How many of those are scams |
| **569** | How many scam messages the search is actually allowed to find |
| **609** | Total searchable pieces = 569 messages + 26 advisory sections + 10 tactics + 4 brand denials |

**What's in the scams:** casino/gambling 420, bank impersonation 70, prize 22,
loan 10, package delivery 8, crypto 2, job offers 2, unclassified 193.

**Which brands get impersonated:** GCash 34, BDO 30, UnionBank 27, Maya 6, BPI 1.

## Why only 569 of 1,571 are searchable

This is the part panelists like, because it shows curation rather than dumping.

> We deliberately hide about two-thirds of our own messages from the search.
> Four reasons:

| We hide | How many | Plain reason |
|---|---|---|
| Legitimate messages | 844 | Our library is *evidence of scams*. We keep the legit ones to test against, but a legit message is not evidence that something is a scam. |
| Test-set messages | 88 | These are our exam questions. If the system can look up the answers to its own exam, our score means nothing. |
| Very short fragments | 6 | Things like `"Hello"`, `"Hi po"`, `"getcash!!"`. Labelled scam in the original data, but there's no pattern there to match against. |
| Near-identical copies | 106 | The same scam re-sent with one number or one link changed — 14 near-identical "earn 500P watching YouTube" texts, 9 variations of the same BDO message. |

Nothing is deleted. Every row stays in the database; we just mark it
"not searchable." The evidence stays auditable, the search pool stays clean.

---

# 3. Why was this specific data collected?

## Say it like this

> Every source answers a question the others can't.
>
> **The Filipino text messages** are the only real local ground truth we could
> get. An AI trained on global phishing data doesn't know that a Cyrillic-letter
> domain like `9910.омск.рус` is a Philippine online-casino lure, or that "naka-hold
> ang account mo" is how a bank scam opens here. This is what makes the answer
> *locally* right instead of just generically plausible.
>
> **The brands' own denials** are there because the strongest possible reply to
> "BDO says your account is restricted" is BDO's own published sentence saying
> they never send links by text. Not our paraphrase. Their words.
>
> **The reporting hotlines** are there because our product's whole output is
> *verdict, explanation, next steps* — and "next steps" is useless without a real
> number to call. I-ARC 1326 is first on the list because it's the single joint
> hotline for DICT, CICC, NPC, and NTC.
>
> **The named tactics** are there so the explanation can say "this is a
> countdown-pressure trick" instead of vaguely pointing at the message. An
> elderly user who learns the *shape* of the trick can spot the next one.
>
> **The Tagalog and English keyword fields** on every entry exist because our
> users write Taglish and most of the source material is English.
>
> **The legitimate messages** stay in the database as our control group — they're
> how we prove the system doesn't just shout "scam" at everything.

## The honesty line

> Our tactic frequencies are **measured from our own corpus**, not quoted from
> elsewhere. We had one number that came from outside — a claim that two-thirds
> of scam texts contain no link at all. We checked it against our own data and
> it's 3.8%, off by a factor of about seventeen. We replaced it with what we
> actually measured.

## Design constraint worth naming

Everything is in **one SQL database**, one table per source. That's mentor
ruling 8 from `docs/2026-07-29-capstone-mentor-consultation.md` — cleaner than
loose CSV files, which would force the retrieval step to jump between files.

---

# 4. How does the knowledge base work?

## Say it like this

> It's built by a script, not by hand, so anyone can reproduce it. The script
> runs the same steps in the same order every time:
>
> 1. Download the message corpus and check the counts.
> 2. Read our curated files — the tactics, the brand denials, the hotlines.
> 3. Clean up the message text.
> 4. Merge exact duplicates.
> 5. Tag each message with what kind of scam it is and which brand it fakes.
> 6. Mark which messages belong to our test set, so they get hidden.
> 7. Find and hide the near-identical copies.
> 8. Flatten everything into one searchable pile.
> 9. Write out the database, plus a build report and an auto-generated
>    attribution file.
>
> Then a **verification script has to pass**. If it fails, the build isn't
> finished. It checks that we're not leaking test answers, that every hotline
> we serve traces to a dated source, and that the filters actually fired.

## Three mechanisms worth explaining if asked

### "How do you stop the test answers from leaking?"

> We match messages on an **identity fingerprint**, not on how they look.
> Everything gets lowercased and all punctuation and spaces are stripped away —
> and we keep Cyrillic letters, because scammers use lookalike Russian
> characters in their fake domains.
>
> Why bother? Two real bugs. Our test file cuts messages off at 400 characters,
> so five test messages are just the beginning of longer messages still in the
> library. And two messages in our corpus differed by **a single space** before a
> URL — one was in our test set, its twin was searchable. The system could have
> looked up the answer to its own exam question. The fingerprint approach caught
> both.

*Technical: `_NON_IDENTITY = re.compile(r"[^0-9a-zЀ-ӿ]+")` in `kb/normalise.py`,
exact-or-prefix matching, `MIN_KEY_LEN = 20`. Verified: 88 holdouts, 0 leaks,
0 false collisions. `backend/tests/test_holdout.py` locks the invariant.*

### "How do you find near-identical messages?"

> We chop each message into overlapping five-character slices and measure how
> much two messages overlap. Above 80% overlap, we call them the same template
> and keep only the longest one, since it carries the most detail.
>
> Ordinary duplicate-detection can't catch these, because the copies differ by
> an amount, a domain, or a greeting — they're not identical, they're
> *near*-identical. We found 52 template families this way.

*Technical: Jaccard similarity over character 5-shingles of the identity key,
threshold 0.8, in `kb/dedupe.py`. The threshold was measured against this
corpus — lower starts merging genuinely different lures that share boilerplate.*

### "Do you throw the filtered data away?"

> No. Nothing is deleted. We only flip a `retrievable` flag to 0. Every message
> stays in the database and can be audited — we just don't let the search see it.

---

# 5. How does RAG work in our system, and why use it?

## First, translate the term itself

> **RAG** stands for Retrieval-Augmented Generation. That sounds complicated;
> it isn't.
>
> An AI answering from memory is a student taking a closed-book exam. RAG is
> the same student with an open book — before it answers, we go find the six
> most relevant pages from *our* book and put them on the desk in front of it.
>
> The important thing to understand is that **nothing in the search actually
> "understands" the message**. It converts text into numbers and measures
> distance. That's the entire mechanism. Everything else is engineering around
> that one idea.

## The core idea, in one analogy

> A model called `multilingual-e5-small` turns any piece of text into a list of
> **384 numbers** — think of it as a coordinate, a specific location on a map.
> It was trained so that text with *similar meaning* lands in a similar place,
> no matter what language it's in or what words it uses.
>
> "Naka-hold ang account mo" and "your account has been suspended" don't share a
> single word — but they land almost on top of each other on this map.
>
> That's why we chose a **multilingual** model. An English-only one would put
> the Taglish version somewhere completely unrelated.
>
> Searching, then, is just: put the user's message on the map, and find the six
> nearest things. That comparison is one line of code and it runs on all 609
> entries at once.

## The five steps

### Step 1 — Redact

> Before anything else, we strip out OTPs, account numbers, card numbers, phone
> numbers, and email addresses. The user's raw message **never** enters the
> system's memory and is never written to a log. Only the redacted version moves
> forward. This is a hard rule, not a preference.

### Step 2 — The translation hop (our contribution)

> Here's the problem: **our library is mostly English, and our users write
> Taglish.** We could just throw the Taglish text at the English library and hope
> the multilingual model bridges the gap — but hoping isn't a design.
>
> So before searching, we spend one AI call rewriting the message into three to
> six short English **red-flag concepts that describe the tactic, not the
> words**:
>
> ```
> ["unexpected prize win", "urgency deadline", "claims account suspended"]
> ```
>
> Now we're searching an English library with English concepts, and the bridge
> is explicit instead of accidental.

### Step 3 — Search (this is the RAG part)

> We search with the concepts **and** the original message text at the same
> time, because they do different jobs:
>
> - the **concepts** cross the language gap and describe the trick
> - the **original text** catches things a paraphrase would lose — a specific
>   brand name, a specific web domain, a specific number
>
> Each of those searches votes independently, and every entry in our library
> keeps its single best score across all of them. We take the top six.
>
> **Why "best score" and not "average score"?** Averaging punishes specialists.
> An entry that perfectly nails "shortened link" but has nothing to do with the
> other four concepts would get dragged down to the middle and lose to something
> vaguely related to everything. In evidence-gathering you want the strongest
> proof for *any* angle, not the most inoffensive compromise across all of them.

*Technical: `(query_vectors @ self._vectors.T).max(axis=0)` — `store.py:94`.
Vectors are normalized so cosine similarity reduces to a plain dot product.
Full numpy scan, no vector index: at 609 rows brute force beats any tree, and an
index would be a dependency and a build step for nothing.*

### Step 4 — Ground the verdict

> Those six pieces of evidence go into the Detector's prompt. It weighs them and
> produces a verdict with a confidence score. If confidence is low, a
> self-reflection step re-examines the judgment — **once**, never in a loop.

### Step 5 — The hotlines, which are deliberately NOT RAG

This is the most important design decision in the whole retrieval layer. Say it
exactly like this:

> Evidence is fetched by similarity. **Hotlines and official links are not.**
> Those are looked up by exact ID, like a phonebook, and handed to the Advisor as
> data to reproduce word for word.
>
> The reason is simple: a similarity search is roughly 90% right. For a piece of
> evidence the AI is weighing, 90% right is fine. For a **phone number handed to
> a panicking 70-year-old, 90% right is just wrong.** That is the one failure
> this product cannot survive.
>
> The file that does this lookup opens with a one-line comment: *"No similarity
> search, ever."*

## Why use RAG at all?

> Three options were on the table.
>
> **Just ask the AI from memory.** It doesn't reliably know what BDO's *current*
> advisory says, or that a specific Cyrillic domain is a Philippine casino lure.
> Those aren't things it learned.
>
> **Fine-tune a model on our data.** Costs money, needs a large labelled dataset
> we don't have, and has to be redone from scratch every time we change models.
>
> **Put the whole library in every prompt.** We'd pay for 609 entries to use 6,
> on every single request.
>
> **RAG.** We pay for six. And updating the knowledge base means editing a text
> file and re-running a script — which matters a lot when the domain expert on
> the team is a student, not a machine-learning engineer.

## One more safety property worth mentioning

> Hidden entries — test-set messages, legitimate messages, fragments — aren't
> filtered out when you search. They're **never loaded into the search in the
> first place.** So no query can return them, even by accident, even if someone
> later forgets the rule. The protection is built into the structure, not into
> somebody remembering.

---

# What we optimized, and what we can prove

Be careful here. There are things we *measured* and things we *reasoned*, and a
panelist will find the seam if we blur it.

## The one measured improvement

> We discovered that **23% of our searchable messages were near-identical
> copies** of each other. That meant the six pieces of evidence we handed the AI
> often contained only two or three genuinely different things — in the worst
> case, four of the six were copies.
>
> We removed them: 675 searchable messages down to 569.
>
> **Result, measured on both versions under identical conditions:** the average
> query went from 5.4 genuinely different messages in its six slots to **6.0**,
> and the worst case went from **2 to 6**. Our type-correct recall — did we fetch
> the right *kind* of scam — rose from **0.800 to 0.829**.
>
> It also killed our own earlier plan. We had been considering cutting the
> retrieval window from 6 down to 3, because slots 4-6 seemed to add nothing.
> Once the duplicates were gone, those slots started earning their place. We
> dropped the plan.

That last sentence is worth keeping. It shows the measurement changed a decision,
which is what separates real evaluation from decoration.

## What we reasoned but did not A/B test

Say these as design choices with justifications, **not** as measured wins:

- Translating to English concepts before searching
- Searching with concepts *and* raw text together
- Taking each entry's best score rather than its average
- The `query:` / `passage:` prefixes the embedding model requires
- Brute-force search instead of a vector index

## What we have NOT measured — say this before they ask

> Our end-to-end accuracy score **structurally cannot see whether retrieval
> helped.** Two completely different situations produce the same score:
> retrieval fetched garbage and the AI guessed right from the message alone, or
> retrieval fetched perfect evidence and the AI used it. Both look like a win.
>
> The test that separates them is an **ablation** — run the whole evaluation
> twice, once with retrieval on and once with it returning nothing, and compare.
> That costs about 680 AI calls and we haven't run it yet. It's our next step.
>
> Related: just measuring similarity with no AI involved at all already reaches
> 0.824 accuracy on our data. That's the floor our full pipeline has to beat, and
> it's the number a panelist is most likely to spring on us.

Do **not** claim a verdict-accuracy improvement from the deduplication. It hasn't
been measured. The retrieval numbers are strong enough on their own.

---

# Jargon → plain language cheat sheet

Keep this open during Q&A.

| If you'd say | Say instead |
|---|---|
| RAG / retrieval-augmented generation | Open-book exam — we find the relevant pages before the AI answers |
| Embedding | Turning text into a coordinate on a meaning-map |
| Vector / 384 dimensions | A list of 384 numbers that locates a piece of text on that map |
| Cosine similarity / dot product | How close two pieces of text are on the map |
| Chunk | One searchable piece of text in our library |
| Corpus | Our collection of real messages |
| Top-k / TOP_K = 6 | The six closest matches |
| Recall@6 | Out of the six things we fetched, did the right kind appear? |
| Holdout / eval set | Our exam questions, hidden from the system |
| Ablation | Turning a feature off to see if it was doing anything |
| Baseline | The dumbest possible method — what we have to beat to justify the complexity |
| Deduplication | Removing repeated copies |
| Jaccard similarity over shingles | Chopping text into overlapping slices and measuring the overlap |
| Normalisation | Cleaning text into a consistent form before comparing |
| Multilingual model | It handles Tagalog and English on the same map |
| Semantic search | Searching by meaning instead of by matching words |
| Keyed lookup / primary key | Looking something up exactly, like a phonebook |
| Hard negatives | Legitimate messages we keep on purpose, to prove we don't cry scam at everything |
| Provenance | Being able to point at where every single fact came from |
| Invariant | A rule the system is not allowed to break |
| Load-time exclusion | It's not in the search at all, so it can't come back by mistake |

---

# The 60-second version

If you get one minute and one question — *"tell us about your data"* — say this:

> We built a Philippine scam library from two kinds of sources. The scam
> examples are 1,571 real Filipino text messages from a public research dataset,
> and the counter-advice comes straight from the organisations that published it
> — GCash, BDO, UnionBank, Maya, the PNP Anti-Cybercrime Group, the NTC. Every
> quote and every hotline in our database was copied from a page we actually
> visited, with the date recorded. When the Bangko Sentral's site was down every
> time we tried, we removed their hotline rather than type it from memory.
>
> We only let the system search 569 of those messages. We hide the legitimate
> ones, we hide our test set so it can't look up its own answers, and we found
> and removed 106 near-identical template copies — which raised the number of
> genuinely different pieces of evidence per query from 5.4 to a full 6.
>
> When a user pastes a message, we redact their private details, translate the
> message into English red-flag concepts so Taglish can reach an English
> library, find the six closest matches, and hand those to the AI as evidence.
> The hotline it gives back at the end is *not* found by search — that one's
> looked up exactly, because a nearly-right phone number given to a frightened
> elderly person is worse than none at all.

---

## Where to check anything in here

| Claim | Verify in |
|---|---|
| Every count in this document | `knowledge-base/out/build_report.json` |
| Source list, URLs, dates, licences | `knowledge-base/ATTRIBUTION.md` (auto-generated) |
| Which fetches worked and which failed | `knowledge-base/content/fetch_log.json` |
| The filters and their justifications | `knowledge-base/README.md` |
| Retrieval mechanism in depth | `docs/rag-explained.md` |
| Optimization evidence, tier by tier | `docs/2026-08-10-rag-use-and-optimization.md` |
| Mentor ruling on the single-SQL-database design | `docs/2026-07-29-capstone-mentor-consultation.md` (ruling 8) |
