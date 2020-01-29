module.exports = {
  owner: {
    username: Cypress.env('ADMIN_USERNAME'),
    password: Cypress.env('ADMIN_PSW'),
  },
  admin: {
    username: Cypress.env('ADMIN_PROFILE_USERNAME'),
    password: Cypress.env('ADMIN_PROFILE_PSW'),
  },
  concierge: {
    username: Cypress.env('ADMIN_USERNAME'),
    password: Cypress.env('ADMIN_PSW'),
  },
  usher: {
    username: Cypress.env('USHER_USERNAME'),
    password: Cypress.env('USHER_PSW'),
  },
  user: {
    username: Cypress.env('MEMBER_USERNAME'),
    password: Cypress.env('MEMBER_PSW'),
  },
};
