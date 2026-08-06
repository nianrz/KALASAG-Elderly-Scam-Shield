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

The privacy line sits under the button because that is where hesitation happens. The freshness date is a limitation stated honestly, not fine print.

The submit button is full-width and the only primary action on screen.

### 2. Analysing

Replace the button with a static progress indicator and a plain-language step label — *Binabasa ang mensahe → Hinahanap ang mga katulad na scam → Sinusuri ang mga red flag → Inihahanda ang payo*.

Steps are shown because a 20-second wait with no feedback reads as broken. They are **not** a progress bar with a percentage, which would be a lie about remaining time.

### 3. Result

```
┌──────────────────────────────────────────────┐
│  Kalasag                      [ EN | TL ]    │
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

## Components

| Component | Responsibility |
|---|---|
| `LanguageToggle` | Two-button segmented control, never a dropdown. Re-renders copy without re-running analysis. Persists to `localStorage`. |
| `InputPanel` | Textarea, submit button, privacy note, freshness badge. Disabled while analysing. |
| `AnalysingState` | Static indicator + step label. |
| `VerdictCard` | Icon, headline, one-line summary. The largest element on screen. |
| `NextSteps` | Ordered list. Hotlines rendered as `tel:` links, since these are the numbers we *want* tapped. |
| `RedFlagList` | Bulleted; each flag is a bold label plus a plain-language detail line. |
| `SimilarScams` | Collapsed `<details>`. Corpus examples, plain text, links inert. |
| `AnalysedMessage` | Collapsed `<details>`. Shows the message as the pipeline analysed it — the API's `redacted_text`, where removed values appear as `[OTP]`-style labels — plus a list of what was removed. Never the raw input, and rendered as plain text so links stay inert. |
| `ContactList` | Rendered inside `NextSteps`, not standalone. Numbers come from the API verbatim. |
| `ErrorState` | Plain-language failure plus a retry button. Never shows a stack trace or the submitted text. |

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

Analysing step labels (`analysing.1`–`analysing.4`) follow the sequence in § Analysing, in both languages. Verdict headlines and subtitles (`verdict.*`) follow the § Verdict visual language table.

Explanation and next-steps text is generated by the Advisor at request time and is not in `i18n.ts` — only the frame is static.

`app.title` is the bare **Kalasag**, identical in both languages, per the rule against translating app names. The longer `Kalasag — Elderly Scam Shield` is for doc titles and the deck; it does not fit the 390px header and the subtitle is not what a panicking user needs to read first.

## States to build

Every one of these is reachable and needs a design, not just the happy path.

| State | Behaviour |
|---|---|
| Empty input submitted | Inline message under the textarea. Do not disable the button — a disabled button with no explanation is worse. |
| Analysing | Step indicator, input disabled, no cancel (a cancel that leaves a half-run graph is worse than waiting). |
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
- Language toggle stays reachable in the header at every breakpoint.

## Out of scope

Dark mode · onboarding or tour · history of past checks · sharing a result · animation beyond the loading state · screenshot upload UI (future work, per the PRD).
