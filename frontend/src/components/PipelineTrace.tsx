import type { AnalyzeResponse } from '../api'
import type { Language } from '../i18n'
import { t } from '../i18n'

interface Props {
  result: AnalyzeResponse
  language: Language
}

function StageBadge({ label }: { label: string }) {
  return (
    <span className="rounded-md bg-paper-deep px-2 py-0.5 text-sm font-bold text-ink-soft">
      {label}
    </span>
  )
}

function StageHeading({
  number,
  title,
  badge,
}: {
  number: number
  title: string
  badge: string
}) {
  return (
    <h4 className="flex flex-wrap items-center gap-2 font-bold text-shield-deep">
      <span
        aria-hidden="true"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-shield font-bold text-white"
      >
        {number}
      </span>
      {title}
      <StageBadge label={badge} />
    </h4>
  )
}

// What each pipeline stage did to this one analysis, for the caregiver and
// the demo — never opened by accident, so it may show the confidence the
// primary result area deliberately hides. Chunk IDs are shown as IDs only;
// the retrieved text already surfaces via SimilarScams.
export function PipelineTrace({ result, language }: Props) {
  const citedChunkIds = [
    ...new Set(
      result.red_flags
        .map((flag) => flag.chunk_id)
        .filter((id): id is string => id !== null),
    ),
  ]

  return (
    <details
      data-testid="pipeline-trace"
      className="rounded-xl border-2 border-line bg-white px-4 py-3"
    >
      <summary className="min-h-11 cursor-pointer content-center font-bold text-shield-deep">
        {t(language, 'trace.summary')}
      </summary>

      <div className="mt-3 space-y-4 text-base break-words">
        <section data-testid="trace-stage">
          <StageHeading
            number={1}
            title={t(language, 'trace.preprocess')}
            badge={t(language, 'trace.noLlm')}
          />
          <p className="mt-1 text-ink-soft">{t(language, 'trace.preprocessDetail')}</p>
          <p className="mt-1">{t(language, 'trace.type', { type: result.message_type })}</p>
          <p>
            {result.redactions.length > 0
              ? t(language, 'trace.removed', { labels: result.redactions.join(' · ') })
              : t(language, 'trace.removedNone')}
          </p>
        </section>

        <section data-testid="trace-stage">
          <StageHeading
            number={2}
            title={t(language, 'trace.retrieve')}
            badge={t(language, 'trace.llm')}
          />
          <p className="mt-1 text-ink-soft">{t(language, 'trace.retrieveDetail')}</p>
          {result.concepts_en.length > 0 ? (
            <>
              <p className="mt-1">{t(language, 'trace.concepts')}</p>
              <ul className="mt-1 flex flex-wrap gap-1.5">
                {result.concepts_en.map((concept) => (
                  <li
                    key={concept}
                    className="rounded-md bg-paper-deep px-2 py-0.5 wrap-anywhere"
                  >
                    {concept}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="mt-1">{t(language, 'trace.conceptsNone')}</p>
          )}
          <p className="mt-2">{t(language, 'trace.matched', { n: result.retrieved.length })}</p>
          <ul data-testid="trace-chunks" className="mt-1 list-disc pl-6">
            {result.retrieved.map((chunk) => (
              <li key={chunk.chunk_id} className="wrap-anywhere">
                {chunk.chunk_id}
                <span className="text-ink-soft"> — {chunk.parent_type}</span>
              </li>
            ))}
          </ul>
        </section>

        <section data-testid="trace-stage">
          <StageHeading
            number={3}
            title={t(language, 'trace.detect')}
            badge={t(language, 'trace.llm')}
          />
          <p className="mt-1 text-ink-soft">{t(language, 'trace.detectDetail')}</p>
          <p className="mt-1 font-bold">{result.verdict}</p>
          <p data-testid="trace-confidence">
            {t(language, 'trace.confidence', { value: result.confidence.toFixed(2) })}
          </p>
          <p>
            {result.reflected
              ? t(language, 'trace.reflected')
              : t(language, 'trace.notReflected')}
          </p>
          {result.low_confidence_reason !== null && (
            <p data-testid="trace-doubt">
              {t(language, 'trace.doubt')}{' '}
              <span className="text-ink-soft">{result.low_confidence_reason}</span>
            </p>
          )}
          {citedChunkIds.length > 0 ? (
            <p className="wrap-anywhere">
              {t(language, 'trace.citedBy')} {citedChunkIds.join(', ')}
            </p>
          ) : (
            <p>{t(language, 'trace.citedNone')}</p>
          )}
        </section>

        <section data-testid="trace-stage">
          <StageHeading
            number={4}
            title={t(language, 'trace.advise')}
            badge={t(language, 'trace.llm')}
          />
          {result.contacts.length > 0 && (
            <p className="mt-1">
              {t(language, 'trace.contactsFrom')}{' '}
              {result.contacts.map((contact) => contact.organisation).join(', ')}
            </p>
          )}
          <p className="mt-1 text-ink-soft">{t(language, 'trace.adviseDetail')}</p>
        </section>

        <p className="border-t-2 border-line pt-3 text-ink-soft">
          {t(language, 'trace.privacyNote')}
        </p>
      </div>
    </details>
  )
}
