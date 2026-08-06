/**
 * Feature: the English | Tagalog output toggle.
 * Contract: docs/PRD.md F8, docs/DESIGN.md § Components.
 *
 * The toggle is a product choice, not language detection. Nothing in the
 * pipeline inspects what language the input was written in.
 */
describe('Language toggle', () => {
  beforeEach(() => {
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
  })

  it('is a segmented control, not a dropdown', () => {
    cy.get('select').should('not.exist')
    cy.get('[data-testid="lang-en"]').should('be.visible')
    cy.get('[data-testid="lang-tl"]').should('be.visible')
  })

  it('switches static UI copy', () => {
    cy.setLanguage('en')
    cy.get('[data-testid="submit"]').should('contain.text', 'Check this message')
    cy.setLanguage('tl')
    cy.get('[data-testid="submit"]').should('contain.text', 'Suriin ang mensahe')
  })

  it('updates the html lang attribute so screen readers pronounce Tagalog', () => {
    cy.setLanguage('tl')
    cy.get('html').should('have.attr', 'lang', 'tl')
    cy.setLanguage('en')
    cy.get('html').should('have.attr', 'lang', 'en')
  })

  it('sends the selected language to the API', () => {
    cy.setLanguage('en')
    cy.analyse('BDO ALERT: Your account is on hold.')
    cy.wait('@analyze').its('request.body.language').should('equal', 'en')
  })

  it('persists the choice across a reload', () => {
    cy.setLanguage('en')
    cy.reload()
    cy.get('[data-testid="lang-en"]').should('have.attr', 'aria-pressed', 'true')
  })

  it('stays reachable in the header at desktop width', () => {
    cy.viewport(1280, 800)
    cy.get('[data-testid="lang-tl"]').should('be.visible')
  })

  // The verdict text, red flags, explanation and next steps come from the
  // model in the language that was submitted. Toggling on a result would flip
  // the labels around them and leave the analysis behind, which reads as a
  // bug. Offering the choice again only where it can still be honoured.
  it('is hidden once a result is on screen, and back after a reset', () => {
    cy.analyse('BDO ALERT: Your account is on hold.')
    cy.get('[data-testid="result"]').should('be.visible')
    cy.get('[data-testid="lang-en"]').should('not.exist')
    cy.get('[data-testid="lang-tl"]').should('not.exist')
    cy.get('[data-testid="reset"]').click()
    cy.get('[data-testid="lang-tl"]').should('be.visible')
  })
})
