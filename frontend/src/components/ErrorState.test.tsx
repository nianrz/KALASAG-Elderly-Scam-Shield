import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ErrorState } from './ErrorState'

describe('ErrorState', () => {
  it('shows a plain-language message and a retry button', () => {
    render(<ErrorState language="tl" onRetry={() => {}} />)
    expect(screen.getByTestId('error')).toHaveTextContent('May problema')
    expect(screen.getByTestId('retry')).toBeVisible()
  })

  it('never renders the submitted text — it does not even receive it', () => {
    render(<ErrorState language="en" onRetry={() => {}} />)
    const text = screen.getByTestId('error').textContent ?? ''
    expect(text).toBe('Something went wrong. Please try again.' + 'Try again')
  })

  it('fires the retry callback', async () => {
    const onRetry = vi.fn()
    render(<ErrorState language="tl" onRetry={onRetry} />)
    await userEvent.click(screen.getByTestId('retry'))
    expect(onRetry).toHaveBeenCalledOnce()
  })
})
