import type { Language, Verdict } from '../i18n'
import { t } from '../i18n'

interface Props {
  verdict: Verdict
  language: Language
}

// Colour is never the only signal: every verdict pairs a background with an
// icon and a word. LIKELY_LEGIT is blue on purpose — green would say "safe".
const TREATMENT: Record<Verdict, { card: string; icon: 'warning' | 'question' | 'info' }> = {
  SCAM: { card: 'bg-scam text-scam-ink', icon: 'warning' },
  LIKELY_SCAM: { card: 'bg-likely-scam text-likely-scam-ink', icon: 'warning' },
  UNCLEAR: { card: 'bg-unclear text-unclear-ink', icon: 'question' },
  LIKELY_LEGIT: { card: 'bg-legit text-legit-ink', icon: 'info' },
}

function VerdictIcon({ kind }: { kind: 'warning' | 'question' | 'info' }) {
  const paths = {
    warning: (
      <>
        <path d="M12 3 2.5 20h19L12 3Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
        <path d="M12 9.5v5" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
        <circle cx="12" cy="17.2" r="1.4" fill="currentColor" />
      </>
    ),
    question: (
      <>
        <circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="M9.6 9.4a2.5 2.5 0 1 1 3.6 2.3c-.8.4-1.2.9-1.2 1.8v.4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
        <circle cx="12" cy="16.8" r="1.3" fill="currentColor" />
      </>
    ),
    info: (
      <>
        <circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="M12 11v5.5" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
        <circle cx="12" cy="7.8" r="1.4" fill="currentColor" />
      </>
    ),
  }
  return (
    <svg viewBox="0 0 24 24" className="h-11 w-11 shrink-0" aria-hidden="true">
      {paths[kind]}
    </svg>
  )
}

export function VerdictCard({ verdict, language }: Props) {
  const { card, icon } = TREATMENT[verdict]
  return (
    <div
      data-testid="verdict"
      data-verdict={verdict}
      role="status"
      className={`rounded-2xl px-6 py-7 shadow-[0_2px_0_rgba(35,40,56,0.18)] ${card}`}
    >
      <div className="flex items-center gap-4">
        <span data-testid="verdict-icon" className="flex">
          <VerdictIcon kind={icon} />
        </span>
        <h2 className="font-display text-[2.1rem] leading-tight font-bold tracking-wide">
          {t(language, `verdict.${verdict}.headline`)}
        </h2>
      </div>
      <p className="mt-3 text-xl font-bold">
        {t(language, `verdict.${verdict}.subtitle`)}
      </p>
    </div>
  )
}
