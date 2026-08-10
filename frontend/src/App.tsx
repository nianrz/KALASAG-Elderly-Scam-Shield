import { useEffect, useState } from 'react'
import type { AnalyzeResponse, MetaResponse } from './api'
import { analyze, fetchMeta } from './api'
import type { Language } from './i18n'
import { t } from './i18n'
import { AnalysedMessage } from './components/AnalysedMessage'
import { ErrorState } from './components/ErrorState'
import { InputPanel } from './components/InputPanel'
import { LanguageToggle } from './components/LanguageToggle'
import { NextSteps } from './components/NextSteps'
import { RedFlagList } from './components/RedFlagList'
import { SimilarScams } from './components/SimilarScams'
import { VerdictCard } from './components/VerdictCard'

type Phase = 'idle' | 'analysing' | 'result' | 'error'

const LANG_KEY = 'kalasag-lang'

function storedLanguage(): Language {
  return localStorage.getItem(LANG_KEY) === 'en' ? 'en' : 'tl'
}

// Crested shield with a gold check, per the Figma mark. Kept in sync by hand
// with public/favicon.svg, which needs literal hexes rather than the theme
// variables — a browser renders a favicon outside the document.
function ShieldMark() {
  return (
    <svg viewBox="0 0 24 24" className="h-9 w-9" aria-hidden="true">
      <path
        d="M4 2.4 8.2 6.2 12 2.4l3.8 3.8L20 2.4v9.3c0 5.1-3.2 9.2-8 10.9-4.8-1.7-8-5.8-8-10.9V2.4Z"
        fill="var(--color-shield)"
      />
      <path
        d="m8 12.6 2.9 2.9 5.4-6"
        fill="none"
        stroke="var(--color-gold)"
        strokeWidth="2.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function App() {
  const [language, setLanguage] = useState<Language>(storedLanguage)
  const [phase, setPhase] = useState<Phase>('idle')
  const [text, setText] = useState('')
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [meta, setMeta] = useState<MetaResponse | null>(null)
  const [metaFailed, setMetaFailed] = useState(false)
  const [inputError, setInputError] = useState(false)

  useEffect(() => {
    document.documentElement.lang = language
    localStorage.setItem(LANG_KEY, language)
  }, [language])

  useEffect(() => {
    fetchMeta().then(setMeta).catch(() => setMetaFailed(true))
  }, [])

  const submit = (message: string) => {
    if (!message.trim()) {
      setInputError(true)
      return
    }
    setInputError(false)
    setPhase('analysing')
    analyze(message, language)
      .then((response) => {
        setResult(response)
        setPhase('result')
      })
      .catch(() => setPhase('error'))
  }

  const reset = () => {
    setText('')
    setResult(null)
    setInputError(false)
    setPhase('idle')
  }

  const kbUnavailable = metaFailed || (meta !== null && (!meta.kb_freshness || meta.chunk_count === 0))

  return (
    <div className="mx-auto flex min-h-dvh max-w-[640px] flex-col px-4 pb-10">
      <header className="flex items-center justify-between gap-4 py-5">
        <div className="flex items-center gap-2.5">
          <ShieldMark />
          <h1 className="font-display text-3xl font-bold text-shield-deep">
            {t(language, 'app.title')}
          </h1>
        </div>
        {/* Hidden on a result: the analysis text is fixed in the language it
            was requested in, so a toggle there would flip only the labels. */}
        {phase !== 'result' && <LanguageToggle language={language} onChange={setLanguage} />}
      </header>

      {kbUnavailable && (
        <p
          data-testid="kb-warning"
          className="mb-4 rounded-xl border-2 border-unclear bg-unclear/40 px-4 py-3 font-bold"
        >
          {t(language, 'kb.warning')}
        </p>
      )}

      {phase !== 'result' && (
        <main>
          <p className="mb-4 text-center font-display text-xl text-ink">
            {t(language, 'app.tagline')}
          </p>
          <InputPanel
            language={language}
            text={text}
            onTextChange={(value) => {
              setText(value)
              if (value.trim()) setInputError(false)
            }}
            onSubmit={() => submit(text)}
            analysing={phase === 'analysing'}
            inputError={inputError}
            meta={meta}
          />
          {phase === 'error' && (
            <div className="mt-4">
              <ErrorState language={language} onRetry={() => submit(text)} />
            </div>
          )}
        </main>
      )}

      {phase === 'result' && result && (
        <main data-testid="result" className="space-y-6">
          <VerdictCard verdict={result.verdict} language={language} />
          {result.explanation && (
            <p className="rounded-xl bg-paper-deep px-4 py-3">{result.explanation}</p>
          )}
          <RedFlagList flags={result.red_flags} language={language} />
          <NextSteps
            steps={result.next_steps}
            contacts={result.contacts}
            language={language}
          />
          <div className="space-y-3">
            <SimilarScams scams={result.similar_scams} language={language} />
            <AnalysedMessage
              redactedText={result.redacted_text}
              redactions={result.redactions}
              language={language}
            />
          </div>
          <p data-testid="uncertainty" className="border-t-2 border-line pt-4 text-ink-soft">
            {t(language, 'result.uncertainty')}
          </p>
          <button
            type="button"
            data-testid="reset"
            onClick={reset}
            className="min-h-14 w-full cursor-pointer rounded-xl border-2 border-shield bg-white text-xl font-bold text-shield transition-colors duration-150 hover:bg-paper-deep"
          >
            {t(language, 'result.again')}
          </button>
        </main>
      )}
    </div>
  )
}
