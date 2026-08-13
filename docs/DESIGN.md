# Design — Kalasag UI

**Owner:** James (UX) · Companion to `PRD.md` and `ARCHITECTURE.md`

The person using this app has just received a message engineered to make them panic. The interface has one job: replace that panic with a clear answer and a concrete next action. Everything below follows from that.

## Design principles

1. **The verdict is the interface.** It is the first thing rendered, the largest thing on screen, and readable without scrolling. Everything else is support.
2. **Never rush the user.** No timers, no countdowns, no auto-dismissing anything. Urgency is the scammer's tool; borrowing it undermines the product.
3. **Legible over dense.** Large type and generous spacing beat fitting more on screen. A user who has to squint is a user who misreads the verdict.
4. **Next steps are actions, not advice.** "Tawagan ang BDO sa 8631-8000" is an action. "Be careful with your account" is not.
5. **Never render anything clickable from the message.** URLs from the input are displayed as inert text. Making the scam link tappable inside the tool that flags it as a scam is the worst possible failure.

## Accessibility rules

Non-negotiable. These are requirement N2 and a stated capstone objective.

| Property | Rule |
|---|---|
| Body text | ≥ 18px. Verdict headline ≥ 32px. |
| Line height | ≥ 1.6 for body copy |
| Contrast | ≥ 4.5:1 for all text; ≥ 3:1 for UI borders and icons |
| Tap targets | ≥ 44 × 44px with ≥ 8px spacing |
| Colour | Never the only signal. Every verdict pairs colour with an icon and a word. |
| Motion | No animation beyond a loading indicator. Respect `prefers-reduced-motion`. |
| Focus | Visible focus ring on every interactive element. Full keyboard operation. |
| Timeouts | None, anywhere. |
| Zoom | Layout holds to 200% browser zoom without horizontal scroll. |
| Language | `<html lang>` updates with the toggle so screen readers pronounce Tagalog correctly. |

## Visual identity

**Revised 2026-08-11 (Allen) to match the Figma prototype; typography and mark revised 2026-08-12.** The palette lives in `@theme` in `frontend/src/index.css` and nothing hard-codes a hex outside it.

| Token | Value | Used for |
|---|---|---|
| `paper` / `paper-deep` | `#f7efe7` / `#efe4d7` | Page background, inset blocks |
| `ink` / `ink-soft` | `#1f2230` / `#4b5162` | Body copy, secondary copy |
| `shield` | `#2222b8` | Primary action, active toggle, step badges |
| `shield-deep` | `#17177f` | Wordmark, section headings, hover, analysing indicator |
| `shield-bright` | `#2b3ce8` | The one accent — the "paste the message" prompt |
| `gold` | `#f0b429` | The check inside the mark, analysing dots |
| `line` | `#e2d7c7` | Borders |

The blues are a saturated indigo, not the muted navy they replaced: on a warm cream page a desaturated blue reads as grey, and the submit button has to be unmistakably the only primary action. Every pair clears the contrast rule above — white on `shield` is 10.6:1, `shield-bright` on paper 6.3:1, white on `scam` (`#c62b1c`) 5.6:1.

**Type:** two faces, and the split is a rule. **Inria Serif 700** sets the `Kalasag` wordmark and nothing else — it is exposed as `font-wordmark`, which appears exactly once in the codebase. **Inter 400/700** sets every other word in the interface, including the verdict headline and the section headings that were previously serif.

This replaced Atkinson Hyperlegible on 2026-08-12 at James's direction, and it is a real trade to record: Atkinson was chosen *because* it disambiguates the glyph pairs low-vision readers confuse — `0`/`O`, `1`/`l`/`I` — which matters in a tool that renders hotline numbers and URLs. Inter does not do that. It keeps the properties the accessibility table actually specifies (a tall x-height at 19px/1.65, and every contrast pair unchanged), so no rule above is broken, but if a user ever misreads a hotline digit, this is the first thing to look at. The mitigation already in place: contacts render at `text-xl` bold, larger than body copy.

**Logo:** `public/kalasag-mark.svg` — James's exported kalasag with a white check. **One file serves both the header and the favicon**, so the tab icon cannot drift from the header the way it did when the two were separate paths. It is a raster embedded in an SVG wrapper: 107 × 178 source against a 44px render, so it is sharp at header size and in the tab, but it will soften if anyone scales it past roughly 60px for a slide or a poster. Redraw it as true paths before using it large.

**The input column is centre-aligned; the result is not.** Tagline, prompt, validation messages, privacy note, freshness date and the error card's message and retry button all centre on the input screen, which is a short symmetrical column and reads as one calm block. Result content stays left-aligned: it is prose and lists, and centred body copy gives a ragged left edge that a low-vision reader has to hunt for on every line.

## Screens

One page, three states. No routing, no navigation.

### 1. Input

```
┌──────────────────────────────────────────────┐
│  Kalasag                      [ EN | TL ]    │
│                                              │
│  I-paste ang mensahe na gusto mong           │
│  masuri.                                     │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │                                        │  │
│  │  (large textarea, ~8 rows)             │  │
│  │                                        │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │           Suriin ang mensahe           │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Hindi namin sine-save ang mensahe mo.       │
│  Huling update ng datos: 06 Aug 2026         │
└──────────────────────────────────────────────┘
```

The privacy line sits under the button because that is where hesitation happens, prefixed by a small `✓` — decorative and `aria-hidden`, since the sentence already carries the promise. The freshness date is a limitation stated honestly, not fine print.

**The freshness line renders on every load, including one where `/api/meta` never answered.** It falls back to `FALLBACK_FRESHNESS` in `InputPanel.tsx` — the KB's own build date. A limitation stated honestly cannot be a limitation that disappears whenever the metadata request fails; and the date is a property of the shipped KB, so a constant beside the component is as true as the endpoint. The KB-unavailable banner, not a missing date, is what tells the user the database is down.

The submit button is full-width and the only primary action on screen.

**The textarea loads prefilled with a sample scam message** — `DEMO_MESSAGE` in `App.tsx`, a Taglish GCash account-lock lure carrying an OTP and a mobile number. It is there so the demo reaches a verdict in one click instead of a paste, and the OTP and number are in it deliberately: they give the redaction line on the result screen something to list. It is sample *input*, not UI copy, so it does not move with the language toggle and has no `i18n` key. The cost is that a real user must clear the box before typing their own message; for a demo build that trade is worth it, and it is the first thing to revisit if this ships to actual users. Reset (*Check another message*) clears the box rather than restoring the sample — the prefill is a first-load affordance, not a sticky default.

### 2. Analysing

Replace the button with a static progress indicator and a plain-language step label — *Binabasa ang mensahe → Hinahanap ang mga katulad na scam → Sinusuri ang mga red flag → Inihahanda ang payo*.

Steps are shown because a 20-second wait with no feedback reads as broken. They are **not** a progress bar with a percentage, which would be a lie about remaining time.

**"Replace the button" means in the button's own slot.** `InputPanel` swaps the indicator in where the button was, so it appears under the user's eye and thumb — it does not render below the privacy and freshness lines, which is where it used to land and which read as a second, unrelated element.

**Only the textarea dims while analysing, never the page.** Dimming the whole screen would grey out the very message the user is waiting on a verdict about, and the disabled textarea is the only thing that actually became uninteractive.

**The animated dots sit to the right of the label and the label carries no ellipsis of its own.** The dots *are* the ellipsis; a label ending in `…` beside three pulsing dots reads as a rendering bug.

### 3. Result

```
┌──────────────────────────────────────────────┐
│  Kalasag                                     │
├──────────────────────────────────────────────┤
│  ⚠  SCAM ITO                                 │
│  Huwag mong i-click o sagutin.               │
├──────────────────────────────────────────────┤
│  BAKIT ITO SCAM                              │
│  • Sinasabing naka-hold ang account mo       │
│    Ang totoong bangko ay hindi nagte-text    │
│    ng link para dito.                        │
│  • May deadline na 24 oras                   │
│    Pressure tactic ito.                      │
├──────────────────────────────────────────────┤
│  ANO ANG GAWIN                               │
│  1. Huwag i-click ang link.                  │
│  2. I-block at i-delete ang mensahe.         │
│  3. Tawagan ang BDO sa (02) 8631-8000.       │
│  4. I-report sa I-ARC: 1326                  │
├──────────────────────────────────────────────┤
│  ▸ Mga katulad na scam (3)                   │
│  ▸ Ang mensahe na sinuri  [OTP removed]      │
├──────────────────────────────────────────────┤
│  Hindi ito 100% tiyak. Kung may duda,        │
│  tanungin ang kapamilya mo.                  │
│                                              │
│  [ Sumuri ng bagong mensahe ]                │
└──────────────────────────────────────────────┘
```

**Order: verdict → why → what to do.** Changed 2026-08-06 (Aki): the explanation and red flags come before the steps so the user understands *why* before being told what to do — the actions land better once the reason is clear. This reverses the original "verdict → what to do → why" order, which optimised for a panicking user who reads only the first two blocks; the verdict card's own subtitle ("Huwag mong i-click o sagutin.") still carries the immediate instruction for that user.

The uncertainty line at the bottom is required on every verdict including `LIKELY_LEGIT`. It is guardrail text, not a disclaimer to be styled away.

Similar scams and the analysed message are collapsed by default — useful for the caregiver, noise for the elderly user.

## Verdict visual language

Colour is never the only signal. Each verdict carries an icon, a word, and a distinct background.

| Verdict | Icon | Tagalog headline | English headline | Treatment |
|---|---|---|---|---|
| `SCAM` | ⚠ | SCAM ITO | THIS IS A SCAM | Red background, white text, heaviest weight |
| `LIKELY_SCAM` | ⚠ | MALAMANG SCAM ITO | LIKELY A SCAM | Orange background, dark text |
| `UNCLEAR` | ? | HINDI SIGURADO | NOT SURE | Amber background, dark text |
| `LIKELY_LEGIT` | ℹ | MUKHANG LEHITIMO | LOOKS LEGITIMATE | Blue background, dark text — **not green** |

`LIKELY_LEGIT` is deliberately not green. Green reads as "safe, you're done", and the one thing the product must never say is that a message is definitely safe. Blue reads as informational, which is what it is.

**Confidence is not shown as a number.** A "68% confident" badge invites a user to reason about a self-reported score that is not calibrated for that purpose. Low confidence is expressed by the `UNCLEAR` verdict and by the wording, which is the honest surface.

### The trace panel is the one exception to the confidence rule

The primary result area still never shows a confidence number — that rule is unchanged. The `PipelineTrace` panel does show it, as `Confidence: 0.91`, in its Detect stage. The reason for hiding the number is that an uncalibrated score confuses a stressed elderly reader; that reason does not apply inside a panel someone must deliberately open, and the number is what makes the Detect stage legible to a caregiver or an evaluator asking "how sure was it?". The narrower rule is enforced by `never displays the model confidence outside the trace panel` in `qa/cypress/e2e/analyse/verdict-variants.cy.ts`, which asserts the value is absent from the verdict, next-steps and uncertainty surfaces and visible only after a click on the trace summary.

**Known rough edge:** the trace displays the Detector's `low_confidence_reason` verbatim, and its language is not guaranteed — `detect.md` specifies the output language for red-flag labels and details but is silent on this field, so it can come back in English on a Tagalog analysis. Tightening the prompt is deliberately out of scope for the trace change, because any prompt edit requires a full eval re-run.

## Components

| Component | Responsibility |
|---|---|
| `LanguageToggle` | Two-button segmented control, never a dropdown. Re-renders copy without re-running analysis. Persists to `localStorage`. Absent from the result view — see § Language is chosen before the analysis. |
| `InputPanel` | Textarea, submit button, privacy note, freshness badge. The textarea dims while analysing, and the submit button's slot holds `AnalysingState` for the duration. |
| `AnalysingState` | Static indicator + step label, with the pulsing dots to the right of the label. |
| `VerdictCard` | Icon, headline, one-line summary. The largest element on screen. |
| `NextSteps` | Ordered list. Hotlines rendered as `tel:` links, since these are the numbers we *want* tapped. |
| `RedFlagList` | Bulleted; each flag is a bold label plus a plain-language detail line. |
| `SimilarScams` | Collapsed `<details>`. Corpus examples, plain text, links inert. |
| `AnalysedMessage` | Collapsed `<details>`. Shows the message as the pipeline analysed it — the API's `redacted_text`, where removed values appear as `[OTP]`-style labels — plus a list of what was removed. Never the raw input, and rendered as plain text so links stay inert. |
| `PipelineTrace` | Collapsed `<details>`, closed by default, at the bottom of the details cluster. Shows what each of the four pipeline stages did for this analysis — Preprocess, Retrieve, Detect, Advise — with chunk IDs, the extracted search concepts, the confidence, and the model's stated doubt. Written for the caregiver and the demo, not the elderly user, who must never meet it by accident. Chunk IDs only, never chunk text — `SimilarScams` already carries the text. |
| `ContactList` | Rendered inside `NextSteps`, not standalone. Numbers come from the API verbatim. |
| `ErrorState` | Plain-language failure plus a retry button. Never shows a stack trace or the submitted text. |

## Language is chosen before the analysis

The toggle appears on the input, analysing and error screens, and **not on the result screen**.

Only the static strings in `i18n.ts` can switch on demand. The verdict headline, red flags, explanation and next steps are written by the model in the language the request carried, and re-running the analysis to translate them costs another three to four LLM calls and roughly forty seconds. Leaving the toggle on the result view meant a click flipped the labels around the analysis and left the analysis itself in the other language — which reads as a bug, and was reported as one. Removing the control is the honest fix: the choice is offered on every screen where it can still be honoured, and `Check another message` returns the user to one.

This is a deliberate limit, not a gap to close later. Translating a finished verdict on demand would need the Advisor's output cached per language or a second call on toggle; neither is worth a week-out change.

## Copy

Every string exists in both languages in `src/i18n.ts`. English is written for the caregiver; Tagalog is written for the elderly user.

**Register rules for Tagalog copy** — the same rules the Advisor prompt follows, applied to static UI text:

- Write Taglish as spoken. `i-click`, `i-block`, `account`, `link`, `text` stay in English because that is what people say.
- Avoid textbook Tagalog: not *panganib* → *delikado*; not *pagpapatunay* → *pag-verify*; not *pagpapatibay* → *pagtiyak*.
- Use *po* in direct address to the user. It is how you speak respectfully to an elder, and its absence reads as curt.
- Never translate brand names, app names, hotline numbers, or agency acronyms.

| Key | English | Tagalog |
|---|---|---|
| `app.title` | Kalasag | Kalasag |
| `input.prompt` | Paste the message you want checked. | I-paste ang mensahe na gusto mong masuri. |
| `input.submit` | Check this message | Suriin ang mensahe |
| `input.privacy` | We don't save your message. | Hindi namin sine-save ang mensahe mo. |
| `input.freshness` | Data last updated: {date} | Huling update ng datos: {date} |
| `result.steps` | What to do | Ano ang gawin |
| `result.why` | Why this is a scam | Bakit ito scam |
| `result.similar` | Similar scams ({n}) | Mga katulad na scam ({n}) |
| `result.analysed` | The message we checked | Ang mensahe na sinuri |
| `result.uncertainty` | This isn't 100% certain. If unsure, ask a family member. | Hindi ito 100% tiyak. Kung may duda, tanungin ang kapamilya mo. |
| `result.again` | Check another message | Sumuri ng bagong mensahe |
| `error.generic` | Something went wrong. Please try again. | May problema. Pakisubukan ulit. |
| `error.empty` | Please paste a message first. | Pakipaste muna ang mensahe. |
| `error.retry` | Try again | Subukan ulit |
| `app.tagline` | Check a message before you trust it | Suriin muna ang mensahe bago magtiwala |
| `input.placeholder` | Paste the SMS, email, or link here… | I-paste dito ang SMS, email, o link… |
| `input.lengthWarning` | This message is very long. Only the first part will be analysed. | Napakahaba po ng mensahe. Ang unang bahagi lang ang masusuri. |
| `kb.warning` | The scam database is unavailable right now. Analysis may be less accurate. | Hindi ma-access ang scam database ngayon. Maaaring hindi gaanong tumpak ang pagsusuri. |
| `result.redactionNote` | We removed these before analysing: | Inalis namin ito bago suriin: |
| `trace.summary` | How this was analysed | Paano ito sinuri |
| `trace.llm` | AI step | AI |
| `trace.noLlm` | no AI | walang AI |
| `trace.preprocess` | Preprocess | Paghahanda |
| `trace.preprocessDetail` | Read the message, worked out what kind it is, and removed sensitive values. | Binasa ang mensahe, tiningnan kung anong klase, at inalis ang mga sensitibong detalye. |
| `trace.type` | Type: {type} | Klase: {type} |
| `trace.removed` | Removed: {labels} | Inalis: {labels} |
| `trace.removedNone` | Nothing sensitive found. | Walang sensitibong nakita. |
| `trace.retrieve` | Retrieve | Paghahanap |
| `trace.retrieveDetail` | Turned the message into English search concepts, then searched the knowledge base. | Ginawang English na concepts ang mensahe, tapos hinanap sa knowledge base. |
| `trace.concepts` | Searched for: | Hinanap: |
| `trace.conceptsNone` | No concepts were extracted; searched with the message text alone. | Walang na-extract na concepts; ang mensahe lang ang ginamit sa paghahanap. |
| `trace.matched` | Matched {n} knowledge-base entries: | {n} tugma sa knowledge base: |
| `trace.detect` | Detect | Pagsusuri |
| `trace.detectDetail` | Weighed the message against those entries and gave a verdict. | Tinimbang ang mensahe laban sa mga entry na iyon at nagbigay ng hatol. |
| `trace.confidence` | Confidence: {value} | Confidence: {value} |
| `trace.reflected` | Ran a second look because confidence was below the threshold. | May pangalawang tingin dahil mababa ang confidence. |
| `trace.notReflected` | Confident enough on the first pass — no second look needed. | Sapat na ang unang tingin — hindi na kailangan ng pangalawa. |
| `trace.doubt` | Stated doubt: | Sinabing duda: |
| `trace.citedBy` | Red flags cite: | Ang mga red flag ay galing sa: |
| `trace.citedNone` | No red flag cited a knowledge-base entry. | Walang red flag na may pinanggalingang entry. |
| `trace.advise` | Advise | Payo |
| `trace.adviseDetail` | Wrote the explanation and next steps. Hotlines were looked up by name, never generated. | Isinulat ang paliwanag at mga susunod na hakbang. Ang mga hotline ay hinanap sa listahan, hindi ginawa-gawa. |
| `trace.contactsFrom` | Contacts looked up: | Mga contact na hinanap: |
| `trace.privacyNote` | Only the redacted message reaches the AI. The original is never saved or logged. | Ang na-redact na mensahe lang ang umaabot sa AI. Hindi sine-save o nilo-log ang orihinal. |

`trace.privacyNote` is worded precisely and must not be loosened: the raw text *does* leave the browser — redaction happens server-side in `preprocess.py`. What is true is that only redacted text reaches the model and nothing raw is stored or logged. Never write "never leaves your device".

Analysing step labels (`analysing.1`–`analysing.4`) follow the sequence in § Analysing, in both languages. Verdict headlines and subtitles (`verdict.*`) follow the § Verdict visual language table.

Explanation and next-steps text is generated by the Advisor at request time and is not in `i18n.ts` — only the frame is static.

`app.title` is the bare **Kalasag**, identical in both languages, per the rule against translating app names. The longer `Kalasag — Elderly Scam Shield` is for doc titles and the deck; it does not fit the 390px header and the subtitle is not what a panicking user needs to read first.

## States to build

Every one of these is reachable and needs a design, not just the happy path.

| State | Behaviour |
|---|---|
| Empty input submitted | Inline message under the textarea. Do not disable the button — a disabled button with no explanation is worse. |
| Analysing | Step indicator in the button's slot, textarea dimmed and disabled, no cancel (a cancel that leaves a half-run graph is worse than waiting). |
| Result, all four verdicts | Per the table above. |
| No red flags found on a `LIKELY_LEGIT` | Show the verdict and the verify-independently line. Do not fabricate a filler bullet. |
| No similar scams | Omit the section entirely rather than showing an empty accordion. |
| KB unavailable | Banner: analysis ran without the knowledge base and may be less accurate. Still show the verdict. |
| Backend unreachable | Error state with retry. Never surface the raw error. |
| Very long input (> 5000 chars) | Accept it, warn that only the first part is analysed. Do not silently truncate. |

## Responsive

Mobile-first. The elderly user is on a phone; the caregiver may be on a laptop.

- Single column at all widths. Max content width 640px, centred.
- No layout that requires horizontal scroll at 320px or at 200% zoom.
- Language toggle stays reachable in the header at every breakpoint, on every screen that still offers the choice.

## Out of scope

Dark mode · onboarding or tour · history of past checks · sharing a result · animation beyond the loading state · screenshot upload UI (future work, per the PRD).
