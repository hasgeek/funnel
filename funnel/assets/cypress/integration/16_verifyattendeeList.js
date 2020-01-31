describe('Verify attendee list', function() {
  const { admin, user } = require('../fixtures/user.js');
  const project = require('../fixtures/project.json');

  it('Verify list of attendees who have responded yes to attending a project', function() {
    cy.relogin('/testcypressproject');
    cy.get('[data-cy-project="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy="see-responses"]').click();
    cy.location('pathname').should('contain', 'rsvp_list');
    cy.get('[data-cy-status="yes"]').click();
    cy.get('[data-cy="user"]').should('contain', user.username);
  });

  after(function() {
    cy.visit('/testcypressproject');
    cy.logout();
  });
});
