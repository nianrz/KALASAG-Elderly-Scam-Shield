/**
 * Feature: PII handling visible to the user.
 * Contract: docs/CLAUDE.md invariant 1, docs/PRD.md N3.
 *
 * The user is told what was removed, without the removed value ever being
 * rendered back to them.
 */
describe('Privacy — redaction', () => {
  it('states the privacy promise before the user submits anything', () => {
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
    // Placed under the button, because that is where hesitation happens.
    cy.get('[data-testid="privacy-note"]')
      .should('be.visible')
      .and('contain.text', 'Hindi namin sine-save')
  })

  it('tells the user what was redacted without showing the value', () => {
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
    cy.analyse('BDO: your OTP is 493021. Verify at http://bdo-verify.cfd')
    cy.wait('@analyze')

    cy.get('[data-testid="analysed-message"]').invoke('attr', 'open', 'open')
    cy.get('[data-testid="analysed-message"]').should('contain.text', 'OTP')
    cy.get('[data-testid="result"]').should('not.contain.text', '493021')
  })

  it('shows the knowledge-base freshness date', () => {
    // A stated limitation, not fine print.
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
    cy.wait('@meta')
    cy.get('[data-testid="freshness"]').should('contain.text', '2026')
  })
})
