const { defineConfig } = require('cypress');

module.exports = defineConfig({
  projectId: '1kvcow',
  chromeWebSecurity: false,
  pageLoadTimeout: 100000,
  video: false,
  experimentalFetchPolyfill: true,
  downloadsFolder: 'tests/cypress/downloads',
  fixturesFolder: 'tests/cypress/fixtures',
  screenshotsFolder: 'tests/cypress/screenshots',
  videosFolder: 'tests/cypress/videos',
  e2e: {
    baseUrl: 'http://funnel.test:3002',
    specPattern: 'tests/cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    supportFile: 'tests/cypress/support.js',
  },
  component: {
    setupNodeEvents(on, config) {},
    specPattern: 'tests/cypress/component/**/*.cy.{js,jsx,ts,tsx}',
  },
});
