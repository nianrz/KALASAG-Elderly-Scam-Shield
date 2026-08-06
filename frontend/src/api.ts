import type { Language, Verdict } from './i18n'

export interface RedFlag {
  label: string
  detail: string
  chunk_id: string | null
}

export interface Contact {
  organisation: string
  hotline: string
  url: string
}

export interface SimilarScam {
  text: string
  scam_type: string | null
}

export interface AnalyzeResponse {
  verdict: Verdict
  confidence: number
  reflected: boolean
  message_type: 'sms' | 'email' | 'url'
  redactions: string[]
  red_flags: RedFlag[]
  explanation: string
  next_steps: string[]
  contacts: Contact[]
  similar_scams: SimilarScam[]
  kb_freshness: string
  model_id: string
}

export interface MetaResponse {
  kb_freshness: string | null
  model_id: string
  chunk_count: number
}

export async function analyze(text: string, language: Language): Promise<AnalyzeResponse> {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  })
  if (!response.ok) throw new Error(`analyze failed: ${response.status}`)
  return response.json()
}

export async function fetchMeta(): Promise<MetaResponse> {
  const response = await fetch('/api/meta')
  if (!response.ok) throw new Error(`meta failed: ${response.status}`)
  return response.json()
}
