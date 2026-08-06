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

      it('never displays a raw confidence percentage', () => {
        // Self-reported confidence is not calibrated for users to reason about.
        cy.get('[data-testid="result"]').should('not.contain.text', '%')
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
