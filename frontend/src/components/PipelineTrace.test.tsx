import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { AnalyzeResponse } from '../api'
import { PipelineTrace } from './PipelineTrace'

const RESULT: AnalyzeResponse = {
  verdict: 'SCAM',
  confidence: 0.91,
  reflected: false,
  message_type: 'sms',
  redactions: ['OTP'],
  redacted_text: 'BDO ALERT: Your [OTP] will expire.',
  red_flags: [
    { label: 'Account on hold', detail: 'Pressure tactic.', chunk_id: 'lure-account-suspended' },
    { label: 'Deadline', detail: 'Urgency.', chunk_id: null },
  ],
  explanation: 'Scam po ito.',
  next_steps: ['Huwag i-click ang link.'],
  contacts: [{ organisation: 'BDO Unibank', hotline: '(02) 8631-8000', url: 'https://www.bdo.com.ph/' }],
  similar_scams: [],
  concepts_en: ['impersonates BDO', 'account lock threat'],
  retrieved: [
    { chunk_id: 'msg00412', parent_type: 'message_example', scam_type: 'bank-impersonation' },
    { chunk_id: 'lure-account-suspended', parent_type: 'lure_pattern', scam_type: 'bank-impersonation' },
  ],
  low_confidence_reason: null,
  kb_freshness: '2026-08-06',
  model_id: 'test-model',
}

describe('PipelineTrace', () => {
  it('renders four stages', () => {
    render(<PipelineTrace result={RESULT} language="en" />)
    expect(screen.getAllByTestId('trace-stage')).toHaveLength(4)
  })

  it('shows the concepts and chunk ids it was given', () => {
    render(<PipelineTrace result={RESULT} language="en" />)
    expect(screen.getByText('impersonates BDO')).toBeInTheDocument()
    expect(screen.getByText('account lock threat')).toBeInTheDocument()
    const chunks = screen.getByTestId('trace-chunks')
    expect(chunks).toHaveTextContent('msg00412')
    expect(chunks).toHaveTextContent('lure-account-suspended')
  })

  it('says no second look was needed when reflected is false', () => {
    render(<PipelineTrace result={RESULT} language="en" />)
    expect(screen.getByText(/no second look needed/)).toBeInTheDocument()
  })

  it('says a second look ran when reflected is true', () => {
    render(<PipelineTrace result={{ ...RESULT, reflected: true }} language="en" />)
    expect(screen.getByText(/Ran a second look/)).toBeInTheDocument()
  })

  it('renders no doubt line when low_confidence_reason is null', () => {
    render(<PipelineTrace result={RESULT} language="en" />)
    expect(screen.queryByTestId('trace-doubt')).not.toBeInTheDocument()
  })

  it('renders the doubt line when the model stated one', () => {
    render(
      <PipelineTrace
        result={{ ...RESULT, low_confidence_reason: 'No similar scam matched closely.' }}
        language="en"
      />,
    )
    expect(screen.getByTestId('trace-doubt')).toHaveTextContent('No similar scam matched closely.')
  })

  it('falls back to the no-concepts line on an empty concepts_en', () => {
    render(<PipelineTrace result={{ ...RESULT, concepts_en: [] }} language="en" />)
    expect(screen.getByText(/searched with the message text alone/)).toBeInTheDocument()
  })

  it('renders in Tagalog', () => {
    render(<PipelineTrace result={RESULT} language="tl" />)
    expect(screen.getByText('Paano ito sinuri')).toBeInTheDocument()
    expect(screen.getByText('Paghahanap')).toBeInTheDocument()
  })

  it('renders in English', () => {
    render(<PipelineTrace result={RESULT} language="en" />)
    expect(screen.getByText('How this was analysed')).toBeInTheDocument()
    expect(screen.getByText('Retrieve')).toBeInTheDocument()
  })
})
