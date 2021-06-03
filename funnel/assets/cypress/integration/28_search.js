describe('Test search feature', function () {
  const project = require('../fixtures/project.json');
  const proposal = require('../fixtures/proposal.json');
  const session = require('../fixtures/session.json');

  it('Search', function () {
    cy.server();
    cy.route('/search?**').as('search');

    cy.visit('/');
    cy.get('input[name="q"]').type('Javascript').type('{enter}');
    cy.get('.tab-content__results').find('.card').contains(project.title);

    cy.get('input[name="q"]')
      .clear()
      .type('testcypressproject')
      .type('{enter}');
    cy.get('.tabs__item').contains('Profiles').click();
    cy.wait('@search');
    cy.get('.tab-content__results')
      .find('.card')
      .contains('testcypressproject');

    cy.get('input[name="q"]').clear().type(proposal.title).type('{enter}');
    cy.get('.tabs__item').contains('Submissions').click();
    cy.wait('@search');
    cy.get('.tab-content__results').contains(proposal.title);

    // cy.get('input[name="q"]')
    //   .clear()
    //   .type(session.title)
    //   .type('{enter}');
    // cy.get('.tabs__item')
    //   .contains('Sessions')
    //   .click();
    // cy.get('.tab-content__results')
    //   .find('.card')
    //   .contains(session.title);
  });
});
