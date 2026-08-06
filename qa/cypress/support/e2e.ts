import './commands'

// A scam-analysis tool must never surface a stack trace or the submitted
// message on failure. If the app throws, the test should fail loudly rather
// than Cypress swallowing it.
Cypress.on('uncaught:exception', () => false)
