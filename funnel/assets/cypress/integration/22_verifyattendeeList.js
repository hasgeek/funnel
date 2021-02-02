describe('Verify attendee list', function () {
  const promoter = require('../fixtures/user.json').promoter;
  const user = require('../fixtures/user.json').user;
  const project = require('../fixtures/project.json');

  it('Verify list of attendees who have responded yes to attending a project', function () {
    cy.login('/testcypressproject', promoter.username, promoter.password);

    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy="see-responses"]').click();
    cy.location('pathname').should('contain', 'rsvp_list');
    cy.get('[data-cy="user"]').should('contain', user.username);
  });
});
