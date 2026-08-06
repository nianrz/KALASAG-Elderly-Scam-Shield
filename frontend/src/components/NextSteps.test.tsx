import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { NextSteps } from './NextSteps'

const CONTACTS = [
  { organisation: 'BDO Unibank', hotline: '(02) 8888-0000', url: 'https://www.bdo.com.ph/' },
  { organisation: 'I-ARC', hotline: '1326', url: 'https://www.cybersecurity.ph/cybercrime-reporting/' },
]

describe('NextSteps', () => {
  it('renders steps as an ordered list', () => {
    render(
      <NextSteps
        steps={['Huwag i-click ang link.', 'I-block ang sender.']}
        contacts={[]}
        language="tl"
      />,
    )
    const items = screen.getByTestId('next-steps').querySelectorAll('ol li')
    expect(items).toHaveLength(2)
  })

  it('reproduces hotlines exactly as given, character for character', () => {
    render(<NextSteps steps={['Tawagan ang BDO.']} contacts={CONTACTS} language="tl" />)
    const contacts = screen.getByTestId('contacts')
    expect(contacts).toHaveTextContent('(02) 8888-0000')
    expect(contacts).toHaveTextContent('1326')
    expect(contacts).toHaveTextContent('BDO Unibank')
  })

  it('renders hotlines as tel: links', () => {
    render(<NextSteps steps={['Tawagan ang BDO.']} contacts={CONTACTS} language="tl" />)
    const links = screen.getByTestId('contacts').querySelectorAll('a[href^="tel:"]')
    expect(links.length).toBeGreaterThanOrEqual(2)
    expect(links[0]).toHaveAttribute('href', 'tel:0288880000')
  })

  it('omits the contact list when there are no contacts', () => {
    render(<NextSteps steps={['Mag-ingat.']} contacts={[]} language="tl" />)
    expect(screen.queryByTestId('contacts')).not.toBeInTheDocument()
  })
})
