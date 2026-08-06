/**
 * Feature: the accessibility rules from docs/DESIGN.md, which are requirement
 * N2 and a stated capstone objective — not polish.
 */
describe('Accessibility', () => {
  beforeEach(() => {
    cy.stubAnalyze('verdict-scam.json')
    cy.visit('/')
  })

  it('renders body text at 18px or larger', () => {
    cy.get('body').invoke('css', 'font-size').then((size) => {
      expect(parseFloat(String(size))).to.be.at.least(18)
    })
  })

  it('gives interactive elements a 44px minimum tap target', () => {
    cy.get('[data-testid="submit"], [data-testid="lang-en"], [data-testid="lang-tl"]').each(($el) => {
      const r = $el[0].getBoundingClientRect()
      expect(Math.min(r.width, r.height), `${$el.attr('data-testid')} tap target`).to.be.at.least(44)
    })
  })

  it('completes a full analysis by keyboard alone', () => {
    cy.get('[data-testid="message-input"]').focus().type('BDO ALERT: account on hold')
    cy.get('[data-testid="submit"]').focus().type('{enter}')
    cy.wait('@analyze')
    cy.get('[data-testid="verdict"]').should('be.visible')
  })

  it('shows a visible focus ring on interactive elements', () => {
    cy.get('[data-testid="submit"]').focus()
      .invoke('css', 'outline-style')
      .then((style) => {
        expect(String(style)).to.not.equal('none')
      })
  })

  it('does not scroll horizontally at 320px', () => {
    cy.viewport(320, 700)
    cy.document().then((doc) => {
      expect(doc.documentElement.scrollWidth).to.be.at.most(doc.documentElement.clientWidth + 1)
    })
  })

  it('does not scroll horizontally at 200% zoom', () => {
    cy.viewport(320, 700)
    cy.get('html').invoke('css', 'font-size', '36px')
    cy.document().then((doc) => {
      expect(doc.documentElement.scrollWidth).to.be.at.most(doc.documentElement.clientWidth + 1)
    })
  })

  it('announces the verdict to assistive technology', () => {
    cy.analyse('BDO ALERT: Your account is on hold.')
    cy.wait('@analyze')
    cy.get('[data-testid="verdict"]').should('have.attr', 'role', 'status')
  })
})
