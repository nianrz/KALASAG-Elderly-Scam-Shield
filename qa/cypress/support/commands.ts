/// <reference types="cypress" />

declare global {
  namespace Cypress {
    interface Chainable {
      /** Stub /api/meta and /api/analyze with a fixture verdict. */
      stubAnalyze(fixture: string): Chainable<void>
      /** Type a message and submit it. */
      analyse(text: string): Chainable<void>
      /** Switch output language via the header toggle. */
      setLanguage(lang: 'en' | 'tl'): Chainable<void>
    }
  }
}

Cypress.Commands.add('stubAnalyze', (fixture: string) => {
  cy.intercept('GET', '/api/meta', { fixture: 'meta.json' }).as('meta')
  cy.intercept('POST', '/api/analyze', { fixture }).as('analyze')
})

Cypress.Commands.add('analyse', (text: string) => {
  cy.get('[data-testid="message-input"]').clear().type(text, { delay: 0 })
  cy.get('[data-testid="submit"]').click()
})

Cypress.Commands.add('setLanguage', (lang: 'en' | 'tl') => {
  cy.get(`[data-testid="lang-${lang}"]`).click()
})

export {}
