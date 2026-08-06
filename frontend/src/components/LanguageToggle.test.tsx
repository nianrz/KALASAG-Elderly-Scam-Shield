import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { LanguageToggle } from './LanguageToggle'

describe('LanguageToggle', () => {
  it('is two buttons, not a dropdown', () => {
    render(<LanguageToggle language="tl" onChange={() => {}} />)
    expect(screen.getByTestId('lang-en')).toBeInTheDocument()
    expect(screen.getByTestId('lang-tl')).toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('marks the active language with aria-pressed', () => {
    render(<LanguageToggle language="tl" onChange={() => {}} />)
    expect(screen.getByTestId('lang-tl')).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('lang-en')).toHaveAttribute('aria-pressed', 'false')
  })

  it('reports the chosen language', async () => {
    const onChange = vi.fn()
    render(<LanguageToggle language="tl" onChange={onChange} />)
    await userEvent.click(screen.getByTestId('lang-en'))
    expect(onChange).toHaveBeenCalledWith('en')
  })
})
