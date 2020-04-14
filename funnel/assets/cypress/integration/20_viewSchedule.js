describe('View schedule of p roject', function() {
  const project = require('../fixtures/project.json');
  const session = require('../fixtures/session.json');
  const proposal = require('../fixtures/proposal.json');
  const user = require('../fixtures/user.json').user;

  it('View schedule', function() {
    cy.server();
    cy.route('**/viewsession-popup').as('view-session');

    cy.visit('/');
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('[data-cy-navbar="schedule"]').click();
    var tomorrow = Cypress.moment()
      .add(1, 'days')
      .format('dddd, D MMMM YYYY');
    cy.get('.schedule__date').contains(tomorrow);
    cy.fixture('venues').then(venues => {
      venues.forEach(function(venue) {
        cy.get('.schedule__row__column--header').contains(venue.room.title);
      });
    });
    cy.get('.schedule__row__column--talks')
      .contains(session.time)
      .click();
    cy.wait('@view-session');
    cy.get('#session-modal').should('be.visible');
    tomorrow = Cypress.moment()
      .add(1, 'days')
      .format('DD MMMM, YYYY');
    cy.get('[data-cy-session="title"]').contains(session.title);
    cy.get('[data-cy-session="speaker"]').contains(session.speaker);
    cy.get('[data-cy-session="time"]').contains(session.time);
    cy.get('[data-cy-session="time"]').contains(tomorrow);
    cy.get('[data-cy-session="room"]').should('have.text', session.venue_room);
    cy.get('#session-modal')
      .find('a.modal__close')
      .click();

    cy.get('.schedule__row__column--talks')
      .contains(proposal.title)
      .click();
    cy.wait('@view-session');
    cy.get('#session-modal').should('be.visible');
    cy.get('[data-cy-session="title"]').contains(proposal.title);
    cy.get('[data-cy-session="speaker"]').contains(user.username);
    cy.get('[data-cy-session="time"]').contains(tomorrow);
    cy.get('[data-cy-session="room"]').should('have.text', proposal.venue_room);
    cy.get('[data-cy="view-proposal"]').should('have.exist');
  });
});
