/**
 * The ONLY spec that hits the real backend and a real LLM.
 *
 * Excluded from `npm run cy:run`. Run it deliberately:
 *     npm run e2e:smoke
 *
 * Requires the backend on :8000 with a working LLM_MODEL and provider key.
 * Costs real tokens. Its job is to catch contract drift between the frontend
 * and the API — the one thing the stubbed suite structurally cannot see.
 */
describe('Smoke — live pipeline', () => {
  it('analyses a known scam end to end', () => {
    cy.visit('/')
    cy.analyse(
      'BDO ALERT: Your account has been temporarily on hold. ' +
        'Verify within 24 hours: http://bdo-secure-verify.cfd/login',
    )

    cy.get('[data-testid="verdict"]', { timeout: 60000 }).should('be.visible')
    cy.get('[data-testid="verdict"]')
      .invoke('attr', 'data-verdict')
      .should('be.oneOf', ['SCAM', 'LIKELY_SCAM'])

    cy.get('[data-testid="next-steps"] li').should('have.length.at.least', 1)
    cy.get('[data-testid="uncertainty"]').should('be.visible')
  })

  it('returns the response shape the frontend expects', () => {
    // Contract check against docs/ARCHITECTURE.md § API.
    cy.request('POST', 'http://localhost:8000/api/analyze', {
      text: 'Magdeposito ng 100P makakuha ng 117P libre. 100k.cfd',
      language: 'tl',
    }).then((res) => {
      expect(res.status).to.equal(200)
      expect(res.body).to.include.keys(
        'verdict', 'confidence', 'reflected', 'message_type', 'redactions',
        'redacted_text', 'red_flags', 'explanation', 'next_steps', 'contacts',
        'similar_scams', 'kb_freshness', 'model_id',
      )
      expect(res.body.verdict).to.be.oneOf(['SCAM', 'LIKELY_SCAM', 'UNCLEAR', 'LIKELY_LEGIT'])
      expect(res.body.confidence).to.be.within(0, 1)
    })
  })
})
