// Every user-facing string, in both languages. English is written for the
// caregiver; Tagalog is written for the elderly user — Taglish as spoken,
// never textbook Tagalog, "po" in direct address.

export type Language = 'en' | 'tl'
export type Verdict = 'SCAM' | 'LIKELY_SCAM' | 'UNCLEAR' | 'LIKELY_LEGIT'

type Copy = typeof en

const en = {
  'app.title': 'Kalasag',
  'app.tagline': 'Check a message before you trust it',
  'input.prompt': 'Paste the message you want checked.',
  'input.placeholder': 'Paste the SMS, email, or link here…',
  'input.submit': 'Check this message',
  'input.privacy': "We don't save your message.",
  'input.freshness': 'Data last updated: {date}',
  'input.lengthWarning': 'This message is very long. Only the first part will be analysed.',
  'kb.warning': 'The scam database is unavailable right now. Analysis may be less accurate.',
  'analysing.1': 'Reading the message',
  'analysing.2': 'Looking for similar scams',
  'analysing.3': 'Checking the red flags',
  'analysing.4': 'Preparing the advice',
  'verdict.SCAM.headline': 'THIS IS A SCAM',
  'verdict.SCAM.subtitle': 'Do not click or reply.',
  'verdict.LIKELY_SCAM.headline': 'LIKELY A SCAM',
  'verdict.LIKELY_SCAM.subtitle': "Be careful — don't respond yet.",
  'verdict.UNCLEAR.headline': 'NOT SURE',
  'verdict.UNCLEAR.subtitle': 'Ask a family member first.',
  'verdict.LIKELY_LEGIT.headline': 'LOOKS LEGITIMATE',
  'verdict.LIKELY_LEGIT.subtitle': 'Still verify independently before acting.',
  'result.steps': 'What to do',
  'result.why': 'Why this is a scam',
  'result.similar': 'Similar scams ({n})',
  'result.analysed': 'The message we checked',
  'result.redactionNote': 'We removed these before analysing:',
  'result.redactionNone': 'Nothing sensitive was found in the message.',
  'result.uncertainty': "This isn't 100% certain. If unsure, ask a family member.",
  'result.again': 'Check another message',
  'error.generic': 'Something went wrong. Please try again.',
  'error.empty': 'Please paste a message first.',
  'error.retry': 'Try again',
}

const tl: Copy = {
  'app.title': 'Kalasag',
  'app.tagline': 'Suriin muna ang mensahe bago magtiwala',
  'input.prompt': 'I-paste ang mensahe na gusto mong masuri.',
  'input.placeholder': 'I-paste dito ang SMS, email, o link…',
  'input.submit': 'Suriin ang mensahe',
  'input.privacy': 'Hindi namin sine-save ang mensahe mo.',
  'input.freshness': 'Huling update ng datos: {date}',
  'input.lengthWarning': 'Napakahaba po ng mensahe. Ang unang bahagi lang ang masusuri.',
  'kb.warning': 'Hindi ma-access ang scam database ngayon. Maaaring hindi gaanong tumpak ang pagsusuri.',
  'analysing.1': 'Binabasa ang mensahe',
  'analysing.2': 'Hinahanap ang mga katulad na scam',
  'analysing.3': 'Sinusuri ang mga red flag',
  'analysing.4': 'Inihahanda ang payo',
  'verdict.SCAM.headline': 'SCAM ITO',
  'verdict.SCAM.subtitle': 'Huwag mong i-click o sagutin.',
  'verdict.LIKELY_SCAM.headline': 'MALAMANG SCAM ITO',
  'verdict.LIKELY_SCAM.subtitle': 'Mag-ingat po — huwag munang sumagot.',
  'verdict.UNCLEAR.headline': 'HINDI SIGURADO',
  'verdict.UNCLEAR.subtitle': 'Tanungin muna po ang kapamilya niyo.',
  'verdict.LIKELY_LEGIT.headline': 'MUKHANG LEHITIMO',
  'verdict.LIKELY_LEGIT.subtitle': 'I-verify pa rin po bago kumilos.',
  'result.steps': 'Ano ang gawin',
  'result.why': 'Bakit ito scam',
  'result.similar': 'Mga katulad na scam ({n})',
  'result.analysed': 'Ang mensahe na sinuri',
  'result.redactionNote': 'Inalis namin ito bago suriin:',
  'result.redactionNone': 'Walang nakitang sensitibong impormasyon sa mensahe.',
  'result.uncertainty': 'Hindi ito 100% tiyak. Kung may duda, tanungin ang kapamilya mo.',
  'result.again': 'Sumuri ng bagong mensahe',
  'error.generic': 'May problema. Pakisubukan ulit.',
  'error.empty': 'Pakipaste muna ang mensahe.',
  'error.retry': 'Subukan ulit',
}

const copies: Record<Language, Copy> = { en, tl }

export function t(lang: Language, key: keyof Copy, vars?: Record<string, string | number>): string {
  let text: string = copies[lang][key]
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.replace(`{${name}}`, String(value))
    }
  }
  return text
}

export const REDACTION_LABELS: Record<Language, Record<string, string>> = {
  en: { OTP: 'a one-time password (OTP)', CARD: 'a card number', ACCOUNT: 'an account number', PHONE: 'a phone number', EMAIL: 'an email address' },
  tl: { OTP: 'isang OTP', CARD: 'isang card number', ACCOUNT: 'isang account number', PHONE: 'isang phone number', EMAIL: 'isang email address' },
}
