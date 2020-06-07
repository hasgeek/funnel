describe('Profile admin roles', function () {
  const owner = require('../fixtures/user.json').owner;
  const admin = require('../fixtures/user.json').admin;
  const profile = require('../fixtures/profile.json');

  it('Check roles of profile admins', function () {
    cy.login('/' + profile.title, admin.username, admin.password);

    cy.get('a[data-cy-btn="edit-details"]').click();
    cy.get('#field-description')
      .find('.CodeMirror textarea')
      .type(profile.description, { force: true });
    cy.get('#logo_url').type(profile.logo_url);
    cy.get('button').contains('Save changes').click();

    cy.get('a[data-cy-btn="profile-crew"]').click();
    cy.get('button[data-cy-btn="add-member"]').should('not.exist');
    cy.get('[data-cy="member"]').contains(admin.username).click();
    cy.get('#member-form', { timeout: 10000 }).should('not.be.visible');
    cy.get('[data-cy="member"]').contains(owner.username).click();
    cy.get('#member-form', { timeout: 10000 }).should('not.be.visible');
  });
});
