describe('Add livestream', function() {
  const editor = require('../fixtures/user.json').editor;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  it('Adding livestream youtube url to project', function() {
    cy.login('/' + profile.title, editor.username, editor.password);

    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="add-livestream"]').click();
    cy.location('pathname').should('contain', '/edit');

    cy.get('#field-livestream_urls')
      .find('textarea')
      .type(project.livestream_url, { force: true });
    cy.get('button')
      .contains('Save changes')
      .click();
    cy.location('pathname').should('contain', project.url);

    cy.get('#livestream').should('exist');
    cy.get('#livestream')
      .find('iframe')
      .should('have.attr', 'src')
      .should('include', project.youtube_video_id);
  });
});
