import { defineConfig } from 'cypress'

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:5173',
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.cy.ts',
    fixturesFolder: 'cypress/fixtures',
    video: false,
    screenshotOnRunFailure: true,

    // The elderly user is on a phone. That is the default viewport, and the
    // desktop caregiver case is asserted explicitly where it matters.
    viewportWidth: 390,
    viewportHeight: 844,

    // A real analysis is 3-4 LLM calls. Stubbed specs are fast; the live smoke
    // spec needs room.
    defaultCommandTimeout: 8000,
    responseTimeout: 60000,
  },
})
