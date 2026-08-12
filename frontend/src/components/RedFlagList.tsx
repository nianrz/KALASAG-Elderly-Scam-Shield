import type { RedFlag } from '../api'
import type { Language } from '../i18n'
import { t } from '../i18n'

interface Props {
  flags: RedFlag[]
  language: Language
}

// Omitted entirely when empty — never fabricate a filler flag.
export function RedFlagList({ flags, language }: Props) {
  if (flags.length === 0) return null
  return (
    <section data-testid="red-flags" aria-label={t(language, 'result.why')}>
      <h3 className="text-2xl font-bold text-shield-deep">
        {t(language, 'result.why')}
      </h3>
      <ul className="mt-3 space-y-4">
        {flags.map((flag, index) => (
          <li key={index} className="border-l-4 border-scam pl-4">
            <p data-testid="flag-label" className="font-bold">
              {flag.label}
            </p>
            <p data-testid="flag-detail" className="text-ink-soft">
              {flag.detail}
            </p>
          </li>
        ))}
      </ul>
    </section>
  )
}
