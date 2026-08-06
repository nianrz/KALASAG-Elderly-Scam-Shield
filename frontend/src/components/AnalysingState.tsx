import { useEffect, useState } from 'react'
import type { Language } from '../i18n'
import { t } from '../i18n'

interface Props {
  language: Language
}

const STEP_KEYS = ['analysing.1', 'analysing.2', 'analysing.3', 'analysing.4'] as const
const STEP_AT_MS = [0, 4000, 10000, 18000]

// A static indicator with a plain-language step label — never a progress
// bar with a percentage, which would be a lie about remaining time.
export function AnalysingState({ language }: Props) {
  const [step, setStep] = useState(0)

  useEffect(() => {
    const timers = STEP_AT_MS.slice(1).map((ms, index) =>
      window.setTimeout(() => setStep(index + 1), ms),
    )
    return () => timers.forEach(window.clearTimeout)
  }, [])

  return (
    <div
      data-testid="analysing"
      role="status"
      aria-live="polite"
      className="flex min-h-14 items-center justify-center gap-4 rounded-xl bg-shield-deep px-6 py-4 text-white"
    >
      <span className="flex gap-1.5" aria-hidden="true">
        <span className="analysing-dot h-2.5 w-2.5 rounded-full bg-gold" />
        <span className="analysing-dot h-2.5 w-2.5 rounded-full bg-gold" />
        <span className="analysing-dot h-2.5 w-2.5 rounded-full bg-gold" />
      </span>
      <span className="font-bold">{t(language, STEP_KEYS[step])}…</span>
    </div>
  )
}
