import type { SimilarScam } from '../api'
import type { Language } from '../i18n'
import { t } from '../i18n'

interface Props {
  scams: SimilarScam[]
  language: Language
}

// Collapsed by default: useful for the caregiver, noise for the elderly
// user. Corpus text renders as plain text — links stay inert.
export function SimilarScams({ scams, language }: Props) {
  if (scams.length === 0) return null
  return (
    <details
      data-testid="similar-scams"
      className="rounded-xl border-2 border-line bg-white px-4 py-3"
    >
      <summary className="min-h-11 cursor-pointer content-center font-bold text-shield-deep">
        {t(language, 'result.similar', { n: scams.length })}
      </summary>
      <ul className="mt-3 space-y-3">
        {scams.map((scam, index) => (
          <li key={index} className="rounded-lg bg-paper-deep px-3 py-2 text-base">
            <p className="break-words">{scam.text}</p>
            {scam.scam_type && (
              <p className="mt-1 text-sm font-bold tracking-wide text-ink-soft uppercase">
                {scam.scam_type}
              </p>
            )}
          </li>
        ))}
      </ul>
    </details>
  )
}
