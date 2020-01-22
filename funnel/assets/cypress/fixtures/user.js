module.exports = {
  admin: {
    username: Cypress.env('ADMIN_USERNAME'),
    password: Cypress.env('ADMIN_PSW'),
  },
  user: {
    username: Cypress.env('MEMBER_USERNAME'),
    password: Cypress.env('MEMBER_PSW'),
  },
};
