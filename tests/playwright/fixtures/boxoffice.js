module.exports = {
  ticket_client: {
    client_id: Cypress.env('BOXOFFICE_CLIENT_ID'),
    secret: Cypress.env('BOXOFFICE_SECRET_KEY'),
    access_key: Cypress.env('BOXOFFICE_ACCESS_KEY'),
    ic_id: Cypress.env('BOXOFFICE_IC_ID'),
  },
};
