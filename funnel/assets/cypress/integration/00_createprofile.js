describe('Login', function() {
  const { admin } = require('../fixtures/user.js');

  it('Create a new project', function() {
    cy.login('/new', admin.username, admin.password);
    cy.wait(60000);

    cy.get('button')
      .contains('Next')
      .click();
    cy.location('pathname').should('contain', '/edit');
    cy.get('#field-description')
      .find('.CodeMirror textarea')
      .type('Test profile', { force: true });
    cy.get('#field-admin_team').click();
    cy.get('.select2-results__option')
      .contains('Owners')
      .click();
    cy.get('button')
      .contains('Save changes')
      .click();
  });
});
