import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Verdict } from '../i18n'
import { VerdictCard } from './VerdictCard'

const CASES: { verdict: Verdict; tl: string; en: string }[] = [
  { verdict: 'SCAM', tl: 'SCAM ITO', en: 'THIS IS A SCAM' },
  { verdict: 'LIKELY_SCAM', tl: 'MALAMANG SCAM ITO', en: 'LIKELY A SCAM' },
  { verdict: 'UNCLEAR', tl: 'HINDI SIGURADO', en: 'NOT SURE' },
  { verdict: 'LIKELY_LEGIT', tl: 'MUKHANG LEHITIMO', en: 'LOOKS LEGITIMATE' },
]

describe('VerdictCard', () => {
  CASES.forEach(({ verdict, tl, en }) => {
    it(`renders ${verdict} with icon and word in both languages`, () => {
      const { rerender } = render(<VerdictCard verdict={verdict} language="tl" />)
      const card = screen.getByTestId('verdict')
      expect(card).toHaveAttribute('data-verdict', verdict)
      expect(card).toHaveTextContent(tl)
      expect(screen.getByTestId('verdict-icon')).toBeInTheDocument()

      rerender(<VerdictCard verdict={verdict} language="en" />)
      expect(screen.getByTestId('verdict')).toHaveTextContent(en)
    })
  })

  it('announces the verdict via role=status', () => {
    render(<VerdictCard verdict="SCAM" language="tl" />)
    expect(screen.getByTestId('verdict')).toHaveAttribute('role', 'status')
  })

  it('never renders a raw confidence percentage', () => {
    render(<VerdictCard verdict="SCAM" language="tl" />)
    expect(screen.getByTestId('verdict').textContent).not.toContain('%')
  })
})
