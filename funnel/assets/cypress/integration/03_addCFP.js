describe('Project', function() {
  const user = require('../../fixtures/user.json');
  const cfp = require('../../fixtures/cfp.json');

  it('Publish project', function() {
    cy.visit('/JSFoo/' + project.url)
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

    cy.get('a[data-cy="add-cfp"]').click();
    cy.wait(500);
  });
});
