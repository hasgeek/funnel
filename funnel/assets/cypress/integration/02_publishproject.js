describe('Project', function() {
  const user = require('../../fixtures/user.json');

  it('Publish project', function() {
    cy.visit('/JSFoo')
      .get('#hgnav')
      .find('.header__button')
      .click();
    cy.get('#showmore').click();
    cy.get('.field-username')
      .type(user.username)
      .should('have.value', user.username);
    cy.get('.field-password')
      .type(user.password)
      .should('have.value', user.password);
    cy.get('.form-actions')
      .find('button')
      .click();

    cy.get('[title="' + project.title + '"]')
      .first()
      .click();
    cy.get('button[data-cy=publish]').click();

    cy.wait(1000);

    cy.get('[data-cy="project-state"]').contains('Published');
  });
});
