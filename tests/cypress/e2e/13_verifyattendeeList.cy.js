/* eslint-disable global-require */
describe('Verify attendee list', () => {
  const { user, promoter } = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');

  it('Verify list of attendees who have responded yes to attending a project', () => {
    cy.login('/testcypressproject', promoter.username, promoter.password);

    cy.get(`[data-cy-title="${project.title}"]`).first().click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy="see-responses"]:visible').click();
    cy.location('pathname').should('contain', 'rsvp_list');
    cy.get('[data-cy="username"]').should('contain', user.fullname);
  });
});
