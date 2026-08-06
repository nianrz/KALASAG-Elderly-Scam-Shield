/**
 * Feature: the SCAM verdict, the highest-stakes path in the product.
 * Contract: docs/DESIGN.md § Result, § Verdict visual language.
 */
describe('Analyse — SCAM verdict', () => {
  beforeEach(() => {
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
    cy.analyse('BDO ALERT: Your account is on hold. Verify: http://bdo-verify.cfd')
    cy.wait('@analyze')
  })

  it('leads with the verdict', () => {
    cy.get('[data-testid="verdict"]').should('be.visible').and('contain.text', 'SCAM ITO')
  })

  it('pairs the verdict with an icon and a word, never colour alone', () => {
    // Accessibility rule: colour is never the only signal.
    cy.get('[data-testid="verdict"]').within(() => {
      cy.get('[data-testid="verdict-icon"]').should('exist')
      cy.contains('SCAM ITO').should('exist')
    })
  })

  it('shows why it is a scam before what to do', () => {
    // Order changed 2026-08-06 (Aki): understanding the why first, then the
    // actions. Reverses the original verdict → steps → why order.
    cy.get('[data-testid="red-flags"]').then(($flags) => {
      cy.get('[data-testid="next-steps"]').then(($steps) => {
        expect($flags[0].compareDocumentPosition($steps[0]))
          .to.equal(Node.DOCUMENT_POSITION_FOLLOWING)
      })
    })
  })

  it('always shows the uncertainty line', () => {
    cy.get('[data-testid="uncertainty"]')
      .should('be.visible')
      .and('contain.text', 'Hindi ito 100% tiyak')
  })

  it('never renders a link from the submitted message as clickable', () => {
    // The worst possible failure: making the scam link tappable inside the
    // tool that just flagged it as a scam.
    cy.get('a[href*="bdo-verify.cfd"]').should('not.exist')
  })

  it('offers a way to check another message', () => {
    cy.get('[data-testid="reset"]').should('be.visible').click()
    cy.get('[data-testid="message-input"]').should('have.value', '')
  })
})
