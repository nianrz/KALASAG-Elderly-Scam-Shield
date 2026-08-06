import type { Language } from '../i18n'
import { REDACTION_LABELS, t } from '../i18n'

interface Props {
  redactedText: string
  redactions: string[]
  language: Language
}

// Shows the message exactly as the pipeline analysed it — redacted values
// appear as [OTP]-style labels, never the originals. Rendered as plain
// text: any link inside stays inert.
export function AnalysedMessage({ redactedText, redactions, language }: Props) {
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
      <p className="mt-3 rounded-lg bg-paper-deep px-3 py-2 text-base break-words whitespace-pre-wrap">
        {redactedText}
      </p>
      <div className="mt-2 text-base text-ink-soft">
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
      </div>
    </details>
  )
}
