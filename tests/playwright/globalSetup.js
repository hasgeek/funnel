//globalSetup.js
const { FullConfig } = require("@playwright/test");
const dotenv = require('dotenv');

async function globalSetup(config) {
  dotenv.config({
    path: '.env.testing',
    override: true
  });
}

module.exports = globalSetup;
