/**
 * Feature: the "How this was analysed" trace panel — observability for the
 * caregiver and the demo. Contract: docs/DESIGN.md § PipelineTrace.
 */
describe('Analyse — pipeline trace panel', () => {
  describe('against a SCAM result', () => {
    beforeEach(() => {
      cy.stubAnalyze('verdict-scam.json')
      cy.visit('/')
      cy.analyse('sample message')
      cy.wait('@analyze')
    })

    it('is present and closed by default', () => {
      // An elderly user must never meet the trace by accident.
      cy.get('[data-testid="pipeline-trace"]')
        .should('exist')
        .and('not.have.attr', 'open')
    })

    it('reveals four stages when opened', () => {
      cy.get('[data-testid="pipeline-trace"] summary').click()
      cy.get('[data-testid="trace-stage"]').should('have.length', 4).and('be.visible')
    })

    it('shows the concepts the retriever searched for', () => {
      cy.get('[data-testid="pipeline-trace"] summary').click()
      cy.fixture('verdict-scam.json').then((res) => {
        res.concepts_en.forEach((concept: string) => {
          cy.get('[data-testid="pipeline-trace"]').should('contain.text', concept)
        })
      })
    })

    it('shows every retrieved chunk id', () => {
      cy.get('[data-testid="pipeline-trace"] summary').click()
      cy.fixture('verdict-scam.json').then((res) => {
        res.retrieved.forEach((chunk: { chunk_id: string }) => {
          cy.get('[data-testid="trace-chunks"]').should('contain.text', chunk.chunk_id)
        })
      })
    })

    it('shows no stated-doubt line when the model stated none', () => {
      cy.get('[data-testid="pipeline-trace"] summary').click()
      cy.get('[data-testid="trace-doubt"]').should('not.exist')
    })
  })

  it('shows the stated-doubt line on an UNCLEAR result', () => {
    cy.stubAnalyze('verdict-unclear.json')
    cy.visit('/')
    cy.analyse('kumusta ka na')
    cy.wait('@analyze')
    cy.get('[data-testid="pipeline-trace"] summary').click()
    cy.fixture('verdict-unclear.json').then((res) => {
      cy.get('[data-testid="trace-doubt"]')
        .should('be.visible')
        .and('contain.text', res.low_confidence_reason)
    })
  })

  it('renders in English', () => {
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
    cy.setLanguage('en')
    cy.analyse('sample message')
    cy.wait('@analyze')
    cy.get('[data-testid="pipeline-trace"] summary')
      .should('contain.text', 'How this was analysed')
  })

  it('renders in Tagalog', () => {
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
    cy.setLanguage('tl')
    cy.analyse('sample message')
    cy.wait('@analyze')
    cy.get('[data-testid="pipeline-trace"] summary')
      .should('contain.text', 'Paano ito sinuri')
  })

  it('never shows the raw submitted OTP anywhere in the result', () => {
    // The trace must not become the one place raw input leaks. The fixture's
    // redacted_text carries [OTP]; the digits typed here must appear nowhere.
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
    cy.analyse('BDO ALERT: Your account is on hold. Send OTP 483920 to verify.')
    cy.wait('@analyze')
    cy.get('[data-testid="pipeline-trace"] summary').click()
    cy.get('[data-testid="result"]').should('not.contain.text', '483920')
  })
})
