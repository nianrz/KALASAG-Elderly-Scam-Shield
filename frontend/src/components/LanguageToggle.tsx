import type { Language } from '../i18n'

interface Props {
  language: Language
  onChange: (lang: Language) => void
}

const OPTIONS: { value: Language; label: string }[] = [
  { value: 'en', label: 'EN' },
  { value: 'tl', label: 'TL' },
]

export function LanguageToggle({ language, onChange }: Props) {
  return (
    <div
      role="group"
      aria-label="Language"
      className="flex rounded-xl border-2 border-line bg-white p-1"
    >
      {OPTIONS.map(({ value, label }) => (
        <button
          key={value}
          type="button"
          data-testid={`lang-${value}`}
          aria-pressed={language === value}
          onClick={() => onChange(value)}
          className={`min-h-11 min-w-11 cursor-pointer rounded-lg px-4 font-bold transition-colors duration-150 ${
            language === value
              ? 'bg-shield text-white'
              : 'bg-transparent text-ink-soft hover:bg-paper-deep'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
