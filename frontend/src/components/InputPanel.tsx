import type { MetaResponse } from '../api'
import type { Language } from '../i18n'
import { t } from '../i18n'

interface Props {
  language: Language
  text: string
  onTextChange: (text: string) => void
  onSubmit: () => void
  analysing: boolean
  inputError: boolean
  meta: MetaResponse | null
}

const LONG_INPUT = 5000

export function InputPanel({
  language, text, onTextChange, onSubmit, analysing, inputError, meta,
}: Props) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit()
      }}
    >
      <label htmlFor="message" className="block text-xl font-bold">
        {t(language, 'input.prompt')}
      </label>
      <textarea
        id="message"
        data-testid="message-input"
        rows={8}
        value={text}
        disabled={analysing}
        placeholder={t(language, 'input.placeholder')}
        onChange={(event) => onTextChange(event.target.value)}
        className="mt-3 w-full resize-y rounded-xl border-2 border-line bg-white px-4 py-3 placeholder:text-ink-soft/60 disabled:opacity-60"
      />
      {inputError && (
        <p data-testid="input-error" role="alert" className="mt-2 font-bold text-scam">
          {t(language, 'error.empty')}
        </p>
      )}
      {text.length > LONG_INPUT && (
        <p data-testid="length-warning" className="mt-2 font-bold text-likely-scam-ink">
          {t(language, 'input.lengthWarning')}
        </p>
      )}
      {!analysing && (
        <button
          type="submit"
          data-testid="submit"
          className="mt-4 min-h-14 w-full cursor-pointer rounded-xl bg-shield text-xl font-bold text-white shadow-[0_3px_0_var(--color-shield-deep)] transition-colors duration-150 hover:bg-shield-deep"
        >
          {t(language, 'input.submit')}
        </button>
      )}
      <p data-testid="privacy-note" className="mt-4 text-center text-base text-ink-soft">
        {t(language, 'input.privacy')}
      </p>
      {meta?.kb_freshness && (
        <p data-testid="freshness" className="mt-1 text-center text-base text-ink-soft">
          {t(language, 'input.freshness', { date: meta.kb_freshness })}
        </p>
      )}
    </form>
  )
}
