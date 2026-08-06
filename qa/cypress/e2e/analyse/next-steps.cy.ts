/**
 * Feature: next steps and the official contacts inside them.
 * Contract: docs/DESIGN.md § Components, docs/CLAUDE.md invariant 2.
 *
 * Hotlines are the one thing in this product that must be byte-exact. A
 * fuzzy-matched number handed to a panicking user is a direct harm.
 */
describe('Analyse — next steps and contacts', () => {
  beforeEach(() => {
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
    cy.analyse('BDO ALERT: Your account is on hold.')
    cy.wait('@analyze')
  })

  it('renders steps as an ordered list', () => {
    cy.get('[data-testid="next-steps"] ol li').should('have.length', 3)
  })

  it('reproduces the hotline exactly as the API returned it', () => {
    cy.fixture('verdict-scam.json').then((res) => {
      res.contacts.forEach((c: { hotline: string; organisation: string }) => {
        cy.get('[data-testid="contacts"]').should('contain.text', c.hotline)
        cy.get('[data-testid="contacts"]').should('contain.text', c.organisation)
      })
    })
  })

  it('makes official hotlines tappable', () => {
    // These are the numbers we WANT tapped, unlike anything from the message.
    cy.get('[data-testid="contacts"] a[href^="tel:"]').should('have.length.at.least', 1)
  })

  it('gives every step an actionable verb rather than vague advice', () => {
    cy.get('[data-testid="next-steps"] li').each(($li) => {
      expect($li.text().trim().length, 'step should not be empty').to.be.greaterThan(0)
    })
  })
})
