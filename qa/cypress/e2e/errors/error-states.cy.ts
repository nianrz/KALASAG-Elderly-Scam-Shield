/**
 * Feature: every failure path a user can actually reach.
 * Contract: docs/DESIGN.md § States to build.
 */
describe('Error states', () => {
  it('blocks an empty submission with an inline message, not a disabled button', () => {
    // A disabled button with no explanation is worse than an error.
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
    cy.get('[data-testid="submit"]').should('not.be.disabled').click()
    cy.get('[data-testid="input-error"]').should('be.visible')
  })

  it('shows a plain-language error when the backend is unreachable', () => {
    cy.intercept('GET', '/api/meta', { fixture: 'meta.json' })
    cy.intercept('POST', '/api/analyze', { forceNetworkError: true }).as('fail')
    cy.visit('/')
    cy.analyse('BDO ALERT: Your account is on hold.')

    cy.get('[data-testid="error"]').should('be.visible')
    cy.get('[data-testid="retry"]').should('be.visible')
  })

  it('never surfaces a stack trace or the submitted message on failure', () => {
    cy.intercept('GET', '/api/meta', { fixture: 'meta.json' })
    cy.intercept('POST', '/api/analyze', {
      statusCode: 500,
      body: { error: { code: 'provider_error', message: 'Upstream failure' } },
    }).as('fail')
    cy.visit('/')
    cy.analyse('BDO ALERT secret-canary-text')
    cy.wait('@fail')

    cy.get('[data-testid="error"]').should('not.contain.text', 'secret-canary-text')
    cy.get('[data-testid="error"]').should('not.contain.text', 'Traceback')
  })

  it('warns rather than silently truncating a very long message', () => {
    cy.stubAnalyze('verdict-unclear.json')
    cy.visit('/')
    // jQuery .val() goes through React's value tracker, which then dedupes
    // the input event — React never sees the change. The native prototype
    // setter bypasses the tracker so the dispatched event reaches React.
    cy.get('[data-testid="message-input"]').then(($el) => {
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value',
      )!.set!
      setter.call($el[0], 'a'.repeat(5200))
      $el[0].dispatchEvent(new Event('input', { bubbles: true }))
    })
    cy.get('[data-testid="length-warning"]').should('be.visible')
  })

  it('still shows a verdict when the knowledge base is unavailable', () => {
    cy.intercept('GET', '/api/meta', { body: { kb_freshness: null, model_id: 'anthropic:claude-opus-5', chunk_count: 0 } })
    cy.intercept('POST', '/api/analyze', { fixture: 'verdict-unclear.json' }).as('analyze')
    cy.visit('/')
    cy.analyse('sample message')
    cy.wait('@analyze')

    cy.get('[data-testid="kb-warning"]').should('be.visible')
    cy.get('[data-testid="verdict"]').should('be.visible')
  })
})
