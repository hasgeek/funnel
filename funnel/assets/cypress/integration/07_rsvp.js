describe('Project', function() {
  const user = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');

  it('RSVP', function() {
    cy.visit('/')
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

    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.wait(1000);
    cy.get('#tickets')
      .find('button[title="Going"]')
      .click();
    cy.get('[data-cy-rsvp="going"]').should('exist');
  });
});
