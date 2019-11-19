describe('Project', function() {
  const admin = require('../fixtures/admin.json');
  const project = require('../fixtures/project.json');

  it('Add labels', function() {
    cy.visit('/')
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

    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.wait(1000);
    cy.get('a[data-cy="labels"').click();
    cy.wait(1000);
    cy.fixture('labels').then(labels => {
      labels.forEach(function(label) {
        cy.get('a[data-cy="add-labels"]').click();
        cy.wait(1000);
        cy.get('#title').type(label.title);
        cy.get('#add-sublabel-form').click();
        cy.wait(500);
        cy.get('#child-form > .ui-dragable-box')
          .eq(0)
          .find('#title')
          .type(label.label1);
        cy.get('#add-sublabel-form').click();
        cy.wait(500);
        cy.get('#child-form > .ui-dragable-box')
          .eq(1)
          .find('#title')
          .type(label.label2);
        if (label.adminLabel) {
          cy.get('#field-restricted')
            .find('label')
            .click();
        }
        cy.get('button[data-cy-submit="save-label"]').click();
        cy.wait(1000);
      });
    });
  });
});
