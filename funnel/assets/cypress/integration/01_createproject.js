describe('Project', function() {
  const admin = require('../fixtures/admin.json');
  const project = require('../fixtures/project.json');

  it('Create a new project', function() {
    cy.visit('/JSFoo/cypress')
      .get('#hgnav')
      .find('.header__button')
      .click();
    cy.get('#showmore').click();
    cy.get('.field-username')
      .type(admin.username)
      .should('have.value', admin.username);
    cy.get('.field-password')
      .type(admin.password)
      .should('have.value', admin.password);
    cy.get('.form-actions')
      .find('button')
      .click();

    cy.get('a[data-cy="new-project"]').click();
    cy.wait(1000);

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
    cy.contains('Create project').click();

    cy.wait(1000);

    cy.title().should('include', project.title);
    cy.get('img[data-cy="bg_image"]').should(
      'have.attr',
      'src',
      project.bg_image
    );
  });
});
