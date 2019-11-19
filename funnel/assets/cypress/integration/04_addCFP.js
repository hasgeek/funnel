describe('Project', function() {
  const admin = require('../fixtures/admin.json');
  const cfp = require('../fixtures/cfp.json');
  const project = require('../fixtures/project.json');

  it('Add CFP', function() {
    cy.visit('/JSFoo/')
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

    cy.get('a[data-cy="add-cfp"]').click();
    cy.wait(1000);
    cy.get('#field-instructions')
      .find('.CodeMirror textarea')
      .type(cfp.instructions, { force: true });
    cy.get('button[name="open-now"]').click();
    var today = Cypress.moment().format('YYYY-MM-DD');
    var cfpEndDay = Cypress.moment(today)
      .add(60, 'days')
      .format('YYYY-MM-DD');
    var time = Cypress.moment().format('HH:mm');
    cy.get('#cfp_end_at-date').type(cfpEndDay);
    cy.get('#cfp_end_at-time').type(time);
    cy.get('button[data-cy="add-cfp"]').click();
    cy.wait(1000);
    cy.get('button[data-cy-cfp=open_cfp]').click();

    cy.wait(1000);

    cy.get('[data-cy="cfp-state"]').contains('Open');
  });
});
