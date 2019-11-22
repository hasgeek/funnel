describe('Project', function() {
  const project = require('../fixtures/project.json');
  const session = require('../fixtures/session.json');

  it('View schedule', function() {
    cy.server();
    cy.route('**/viewsession-popup').as('view-session');

    cy.visit('/');
    cy.get('.upcoming')
      .find('li.card--upcoming')
      .contains(project.title)
      .click();
    cy.get('[data-cy-navbar="schedule"]').click();
    var tomorrow = Cypress.moment()
      .add(1, 'days')
      .format('dddd, DD MMMM YYYY');
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
    var tomorrow = Cypress.moment()
      .add(1, 'days')
      .format('DD MMMM, YYYY');
    cy.get('[data-cy-session="title"]').contains(session.title);
    cy.get('[data-cy-session="speaker"]').contains(session.speaker);
    cy.get('[data-cy-session="time"]').contains(session.time);
    cy.get('[data-cy-session="time"]').contains(tomorrow);
    cy.get('[data-cy-session="room"]').contains(session.room);
  });
});
