describe('Login', function() {
  const { owner } = require('../fixtures/user.js');

  it('Create a new profile', function() {
    cy.server();
    cy.route('POST', '**/login').as('login');
    cy.login('/new', owner.username, owner.password);
    cy.wait('@login', { timeout: 20000 });

    cy.get('button')
      .contains('Next')
      .click();
    cy.location('pathname').should('contain', '/edit');
    cy.get('#field-description')
      .find('.CodeMirror textarea')
      .type('Test profile', { force: true });
    cy.get('button')
      .contains('Save changes')
      .click();
  });
});
