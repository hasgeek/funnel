describe('Project', function() {
  const admin = require('../fixtures/admin.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');
  const labels = require('../fixtures/labels.json');

  it('Confirm proposal', function() {
    cy.login('/JSFoo/', admin.username, admin.password);

    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="proposals"]').click();
    cy.location('pathname').should('contain', 'proposals');
    cy.get('#search').type(proposal.title);
    cy.get('a[data-cy-proposal="' + proposal.title + '"]').click();
    cy.get('#label-select').click();

    cy.get('#label-dropdown label')
      .contains(labels[2].title)
      .click();
    cy.get('#label-select').click();
    cy.get('button[name="add-label"]').click();

    cy.fixture('labels').then(labels => {
      labels.forEach(function(label) {
        cy.get('.label').contains(label.title + ': ' + label.label1);
      });
    });
    cy.get('[data-cy="proposal-status"]')
      .find('button[value="awaiting_details"]')
      .click();
    cy.get('[data-cy="proposal-status"]')
      .find('button[value="under_evaluation"]')
      .click();
    cy.get('[data-cy="proposal-status"]')
      .find('button[value="confirm"]')
      .click();

    cy.get('[data-cy-proposal-status="Confirmed"]').should('exist');
  });
});
