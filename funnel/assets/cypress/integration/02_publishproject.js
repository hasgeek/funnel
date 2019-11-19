describe('Project', function() {
  const admin = require('../fixtures/admin.json');

  it('Publish project', function() {
    cy.visit('/JSFoo')
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

    cy.get('[title="' + project.title + '"]')
      .first()
      .click();
    cy.get('button[data-cy-state=publish]').click();

    cy.wait(1000);

    cy.get('[data-cy="project-state"]').contains('Published');
  });
});
