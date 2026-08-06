import type { Contact } from '../api'
import type { Language } from '../i18n'
import { t } from '../i18n'
import { ContactList } from './ContactList'

interface Props {
  steps: string[]
  contacts: Contact[]
  language: Language
}

export function NextSteps({ steps, contacts, language }: Props) {
  return (
    <section data-testid="next-steps" aria-label={t(language, 'result.steps')}>
      <h3 className="font-display text-2xl font-bold text-shield-deep">
        {t(language, 'result.steps')}
      </h3>
      <ol className="mt-3 space-y-3">
        {steps.map((step, index) => (
          <li key={index} className="flex gap-3">
            <span
              aria-hidden="true"
              className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-shield font-bold text-white"
            >
              {index + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
      <ContactList contacts={contacts} />
    </section>
  )
}
