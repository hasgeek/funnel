const { defineConfig } = require('cypress');

module.exports = defineConfig({
  projectId: '1kvcow',
  chromeWebSecurity: false,
  pageLoadTimeout: 150000,
  video: false,
  downloadsFolder: 'downloads',
  fixturesFolder: 'fixtures',
  screenshotsFolder: 'screenshots',
  videosFolder: 'videos',
  experimentalFetchPolyfill: true,
  viewportWidth: 1280,
  viewportHeight: 800,
  e2e: {
    baseUrl: 'http://funnel.test:3002',
    specPattern: 'e2e/**/*.cy.{js,jsx,ts,tsx}',
    supportFile: 'support.js',
  },
});
