/**
 * Feature: all four verdicts render distinctly and none of them claims safety.
 * Contract: docs/DESIGN.md § Verdict visual language.
 */
const CASES = [
  { fixture: 'verdict-scam.json', verdict: 'SCAM', headline: 'SCAM ITO' },
  { fixture: 'verdict-likely-scam.json', verdict: 'LIKELY_SCAM', headline: 'MALAMANG SCAM ITO' },
  { fixture: 'verdict-unclear.json', verdict: 'UNCLEAR', headline: 'HINDI SIGURADO' },
  { fixture: 'verdict-likely-legit.json', verdict: 'LIKELY_LEGIT', headline: 'MUKHANG LEHITIMO' },
]

describe('Analyse — verdict variants', () => {
  CASES.forEach(({ fixture, verdict, headline }) => {
    describe(verdict, () => {
      beforeEach(() => {
        cy.stubAnalyze(fixture)
        cy.visit('/')
        cy.analyse('sample message')
        cy.wait('@analyze')
      })

      it('renders its own headline', () => {
        cy.get('[data-testid="verdict"]')
          .should('have.attr', 'data-verdict', verdict)
          .and('contain.text', headline)
      })

      it('shows the uncertainty line even on the least alarming verdict', () => {
        // Guardrail: the product never tells anyone a message is definitely safe.
        cy.get('[data-testid="uncertainty"]').should('be.visible')
      })

      it('gives at least one next step', () => {
        cy.get('[data-testid="next-steps"] li').should('have.length.at.least', 1)
      })

      it('never displays the model confidence outside the trace panel', () => {
        // Self-reported confidence is not calibrated for users to reason
        // about, so the primary result area never shows it. The trace panel
        // is the deliberate exception (docs/DESIGN.md § PipelineTrace), so
        // the assertion targets the primary surfaces rather than the whole
        // result. The static "100%" in the uncertainty copy is DESIGN.md's
        // own wording, not a confidence readout.
        cy.fixture(fixture).then((res) => {
          const shown = [`${Math.round(res.confidence * 100)}%`, String(res.confidence)]
          shown.forEach((value) => {
            cy.get('[data-testid="verdict"]').should('not.contain.text', value)
            cy.get('[data-testid="next-steps"]').should('not.contain.text', value)
            cy.get('[data-testid="uncertainty"]').should('not.contain.text', value)
          })
        })
      })

      it('keeps the confidence behind a deliberate click', () => {
        // Closed-<details> content is hidden via content-visibility, which
        // Cypress's visibility algorithm does not understand — so the closed
        // state is asserted on the open attribute, not on the element.
        cy.get('[data-testid="pipeline-trace"]').should('not.have.attr', 'open')
        cy.get('[data-testid="pipeline-trace"] summary').click()
        cy.get('[data-testid="trace-confidence"]').should('be.visible')
      })
    })
  })

  it('does not colour LIKELY_LEGIT green', () => {
    // Green reads as "you are safe, done" — the one thing we must never say.
    cy.stubAnalyze('verdict-likely-legit.json')
    cy.visit('/')
    cy.analyse('sample message')
    cy.wait('@analyze')
    cy.get('[data-testid="verdict"]')
      .invoke('css', 'background-color')
      .then((bg) => {
        const [r, g, b] = String(bg).match(/\d+/g)!.map(Number)
        expect(g, 'green channel should not dominate').to.not.be.greaterThan(Math.max(r, b) + 20)
      })
  })
})
