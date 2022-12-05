/* eslint-disable global-require */
describe('Test search feature', () => {
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');
  const proposal = require('../fixtures/proposal.json');
  const session = require('../fixtures/session.json');

  it('Search', () => {
    cy.server();
    cy.route('/search?**').as('search');

    cy.visit('/');
    cy.get('input[name="q"]').type('Javascript').type('{enter}');
    cy.get('.tab-content__results').find('.card').contains(project.title);

    cy.get('input[name="q"]').clear().type(profile.title).type('{enter}');
    cy.get('.tabs__item').contains('Accounts').click();
    cy.wait('@search');
    cy.get('.tab-content__results').find('.card').contains(profile.title);

    cy.get('input[name="q"]').clear().type(proposal.title).type('{enter}');
    cy.get('.tabs__item').contains('Submissions').click();
    cy.wait('@search');
    cy.get('.tab-content__results').contains(proposal.title);

    cy.get('input[name="q"]').clear().type(session.title).type('{enter}');
    cy.get('.tabs__item').contains('Sessions').click();
    cy.get('.tab-content__results').find('.user__box').contains(session.title);
  });
});
