describe('Project', function() {
  const { admin } = require('../fixtures/user.js');
  const project = require('../fixtures/project.json');

  it('Create a new project', function() {
    cy.login('/revue/new', admin.username, admin.password);
    cy.get('#name').type(project.url);
    cy.get('#title').type(project.title);
    cy.get('#location').type(project.location);
    cy.get('#tagline').type(project.tagline);
    cy.get('#website').type(project.website);
    cy.get('#field-description')
      .find('.CodeMirror textarea')
      .type(project.description, { force: true });
    cy.get('#bg_image').type(project.bg_image);
    cy.get('#allow_rsvp').click();
    cy.get('button')
      .contains('Create project')
      .click();
    cy.location('pathname').should('contain', project.url);

    cy.title().should('include', project.title);
    cy.get('img[data-cy="bg_image"]').should(
      'have.attr',
      'src',
      project.bg_image
    );
  });
});
