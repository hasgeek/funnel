describe('Verify attendee list', function() {
  const concierge = require('../fixtures/user.json').concierge;
  const user = require('../fixtures/user.json').user;
  const project = require('../fixtures/project.json');

  it('Verify list of attendees who have responded yes to attending a project', function() {
    cy.login('/testcypressproject', concierge.username, concierge.password);

    cy.get('[data-cy-project="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy="see-responses"]').click();
    cy.location('pathname').should('contain', 'rsvp_list');
    cy.get('[data-cy-status="yes"]').click();
    cy.get('[data-cy="user"]').should('contain', user.username);
  });
});
