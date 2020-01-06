describe('Project', function() {
  const { admin, baseurl } = require('../fixtures/user.js');
  const project = require('../fixtures/project.json');

  it('Create a new project', function() {
    cy.relogin('/');
    cy.visit('/new');

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
