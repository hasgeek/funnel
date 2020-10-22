describe('Project', function () {
  const admin = require('../fixtures/user.json').admin;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  it('Create a new project', function () {
    cy.login('/' + profile.title, admin.username, admin.password);

    cy.get('a[data-cy="new-project"]').click();
    cy.location('pathname').should('contain', '/new');

    cy.get('#title').type(project.title);
    cy.get('#location').type(project.location);
    cy.get('#tagline').type(project.tagline);
    cy.get('#field-description')
      .find('.CodeMirror textarea')
      .type(project.description, { force: true });
    // cy.get('#bg_image').type(project.bg_image);
    cy.get('button').contains('Create project').click();
    cy.location('pathname').should('contain', project.url);

    cy.title().should('include', project.title);
    // cy.get('img[data-cy="bg_image"]').should(
    //   'have.attr',
    //   'src',
    //   project.bg_image
    // );
  });
});
