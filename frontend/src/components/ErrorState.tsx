import type { Language } from '../i18n'
import { t } from '../i18n'

interface Props {
  language: Language
  onRetry: () => void
}

// Plain-language failure and a retry. Never a stack trace, never the
// submitted text.
export function ErrorState({ language, onRetry }: Props) {
  return (
    <div
      data-testid="error"
      role="alert"
      className="rounded-xl border-2 border-scam bg-white px-5 py-4 text-center"
    >
      <p className="font-bold">{t(language, 'error.generic')}</p>
      <button
        type="button"
        data-testid="retry"
        onClick={onRetry}
        className="mt-3 min-h-11 cursor-pointer rounded-lg bg-shield px-6 font-bold text-white transition-colors duration-150 hover:bg-shield-deep"
      >
        {t(language, 'error.retry')}
      </button>
    </div>
  )
}
