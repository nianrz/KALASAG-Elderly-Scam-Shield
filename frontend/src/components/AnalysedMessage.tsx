import type { Language } from '../i18n'
import { REDACTION_LABELS, t } from '../i18n'

interface Props {
  redactions: string[]
  language: Language
}

// The API returns redaction labels only — the raw message is never echoed
// back, so this section reports what was removed rather than re-rendering
// the message.
export function AnalysedMessage({ redactions, language }: Props) {
  return (
    <details
      data-testid="analysed-message"
      className="rounded-xl border-2 border-line bg-white px-4 py-3"
    >
      <summary className="min-h-11 cursor-pointer content-center font-bold text-shield-deep">
        {t(language, 'result.analysed')}
        {redactions.length > 0 && (
          <span className="ml-2 rounded-md bg-paper-deep px-2 py-0.5 text-sm font-bold text-ink-soft">
            {redactions.join(' · ')}
          </span>
        )}
      </summary>
      <div className="mt-3 text-base text-ink-soft">
        {redactions.length > 0 ? (
          <>
            <p>{t(language, 'result.redactionNote')}</p>
            <ul className="mt-1 list-disc pl-6">
              {redactions.map((label) => (
                <li key={label}>{REDACTION_LABELS[language][label] ?? label}</li>
              ))}
            </ul>
          </>
        ) : (
          <p>{t(language, 'result.redactionNone')}</p>
        )}
        <p className="mt-2">{t(language, 'result.messageHidden')}</p>
      </div>
    </details>
  )
}
