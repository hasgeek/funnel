/* eslint-disable global-require */
describe('Add livestream', () => {
  const { editor } = require('../fixtures/user.json');
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  it('Adding livestream youtube url to project', () => {
    cy.login(`/${profile.title}`, editor.username, editor.password);

    cy.get(`[data-cy-title="${project.title}"]`).first().click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-navbar="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="add-livestream"]').click();
    cy.location('pathname').should('contain', '/edit');

    cy.get('#field-livestream_urls')
      .find('textarea')
      .type(project.livestream_url, { force: true });
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.location('pathname').should('contain', project.url);

    cy.get('#livestream').should('exist');
    cy.get('#livestream')
      .find('iframe')
      .should('have.attr', 'src')
      .should('include', project.youtube_video_id);
  });
});
