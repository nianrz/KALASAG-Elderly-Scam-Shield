/**
 * Feature: red-flag list and the collapsed detail sections.
 * Contract: docs/DESIGN.md § Result, § States to build.
 */
describe('Analyse — red flags and detail sections', () => {
  it('renders each red flag with a label and a plain-language detail', () => {
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
    cy.analyse('BDO ALERT: Your account is on hold.')
    cy.wait('@analyze')

    cy.get('[data-testid="red-flags"] li').should('have.length', 2)
    cy.get('[data-testid="red-flags"] li').first().within(() => {
      cy.get('[data-testid="flag-label"]').should('not.be.empty')
      cy.get('[data-testid="flag-detail"]').should('not.be.empty')
    })
  })

  it('collapses similar scams and the analysed message by default', () => {
    // Useful for the caregiver, noise for the elderly user.
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
    cy.analyse('BDO ALERT: Your account is on hold.')
    cy.wait('@analyze')

    cy.get('[data-testid="similar-scams"]').should('not.have.attr', 'open')
    cy.get('[data-testid="analysed-message"]').should('not.have.attr', 'open')
  })

  it('omits the similar-scams section entirely when there are none', () => {
    // An empty accordion is worse than no accordion.
    cy.stubAnalyze('verdict-unclear.json')
    cy.visit('/')
    cy.analyse('kumusta ka na')
    cy.wait('@analyze')

    cy.get('[data-testid="similar-scams"]').should('not.exist')
  })

  it('does not fabricate a filler red flag when none were found', () => {
    cy.stubAnalyze('verdict-likely-legit.json')
    cy.visit('/')
    cy.analyse('You received PHP 500 from JUAN D.')
    cy.wait('@analyze')

    cy.get('[data-testid="red-flags"]').should('not.exist')
    cy.get('[data-testid="uncertainty"]').should('be.visible')
  })
})
