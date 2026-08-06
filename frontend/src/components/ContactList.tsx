import type { Contact } from '../api'

interface Props {
  contacts: Contact[]
}

// Numbers come from the API verbatim — never reformat a hotline. These are
// the numbers we WANT tapped, unlike anything from the message.
export function ContactList({ contacts }: Props) {
  if (contacts.length === 0) return null
  return (
    <ul data-testid="contacts" className="mt-4 space-y-3">
      {contacts.map((contact) => (
        <li
          key={contact.organisation}
          className="rounded-xl border-2 border-line bg-white px-4 py-3"
        >
          <span className="font-bold">{contact.organisation}</span>
          {contact.hotline && (
            <a
              href={`tel:${contact.hotline.replace(/[^+\d]/g, '')}`}
              className="mt-1 block min-h-11 content-center text-xl font-bold text-shield underline underline-offset-4"
            >
              {contact.hotline}
            </a>
          )}
          {contact.url && (
            <a
              href={contact.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 block break-all text-base text-ink-soft underline underline-offset-2"
            >
              {contact.url}
            </a>
          )}
        </li>
      ))}
    </ul>
  )
}
