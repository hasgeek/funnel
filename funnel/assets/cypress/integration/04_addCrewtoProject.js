describe('Adding crew', function () {
  const owner = require('../fixtures/user.json').owner;
  const admin = require('../fixtures/user.json').admin;
  const concierge = require('../fixtures/user.json').concierge;
  const usher = require('../fixtures/user.json').usher;
  const editor = require('../fixtures/user.json').editor;
  const hguser = require('../fixtures/user.json').hguser;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  Cypress.on('uncaught:exception', (err, runnable) => {
    return false;
  });

  it('Add crew to project', function () {
    cy.login('/' + profile.title, admin.username, admin.password);
    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="crew"]').click();
    cy.get('[data-cy="member"]')
      .contains(admin.username)
      .parents('.member')
      .find('[data-cy="role"]')
      .contains('Editor');

    cy.add_member(concierge.username, 'concierge');
    cy.add_member(usher.username, 'usher');
    cy.add_member(editor.username, 'editor');
    cy.add_member(hguser.username, 'usher', (fail = true));
  });
});
