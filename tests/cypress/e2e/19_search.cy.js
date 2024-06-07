import profile from '../fixtures/profile.json';
import project from '../fixtures/project.json';
import proposal from '../fixtures/proposal.json';
import session from '../fixtures/session.json';

describe('Test search feature', () => {
  it('Search', () => {
    cy.intercept('/search?**').as('search');

    cy.visit('/');
    cy.get('input[name="q"]').type('Javascript');
    cy.get('input[name="q"]').type('{enter}');
    cy.get('.tab-content__results').find('.card').contains(project.title);

    cy.get('input[name="q"]').clear();
    cy.get('input[name="q"]').type(profile.title);
    cy.get('input[name="q"]').type('{enter}');
    cy.get('.tabs__item').contains('Accounts').click();
    cy.wait('@search');
    cy.get('.tab-content__results').find('.card').contains(profile.title);

    cy.get('input[name="q"]').clear();
    cy.get('input[name="q"]').type(proposal.title);
    cy.get('input[name="q"]').type('{enter}');
    cy.get('.tabs__item').contains('Submissions').click();
    cy.wait('@search');
    cy.get('.tab-content__results').contains(proposal.title);

    cy.get('input[name="q"]').clear();
    cy.get('input[name="q"]').type(session.title);
    cy.get('input[name="q"]').type('{enter}');
    cy.get('.tabs__item').contains('Sessions').click();
    cy.get('.tab-content__results').find('.user__box').contains(session.title);
  });
});
