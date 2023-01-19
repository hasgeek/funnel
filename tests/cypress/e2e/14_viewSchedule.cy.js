/* eslint-disable global-require */
describe('View schedule of p roject', () => {
  const project = require('../fixtures/project.json');
  const session = require('../fixtures/session.json');
  const proposal = require('../fixtures/proposal.json');
  const { user } = require('../fixtures/user.json');
  const dayjs = require('dayjs');

  it('View schedule', () => {
    cy.server();
    cy.route('GET', '**/schedule/*').as('view-session');

    cy.visit('/');
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('[data-cy-navbar="schedule"]').click();

    cy.get('a[data-cy="add-to-calendar"]').click();
    cy.wait(1000);
    cy.get('[data-cy="schedule-subscribe"]').should('exist');
    cy.get('a[data-cy="close-modal"]').click();

    let tomorrow = dayjs().add(1, 'days').format('dddd, D MMMM YYYY');
    cy.get('.schedule__date').contains(tomorrow);
    cy.fixture('venues').then((venues) => {
      venues.forEach((venue) => {
        cy.get('.schedule__row__column--header').contains(venue.room.title);
      });
    });
    cy.get('[data-cy="session-time"]').contains(session.time).click();
    cy.wait('@view-session');
    cy.get('#session-modal').should('be.visible');
    tomorrow = dayjs().add(1, 'days').format('MMM D, YYYY');
    cy.get('[data-cy-session="title"]').contains(session.title);
    cy.get('[data-cy-session="speaker"]').contains(session.speaker);
    cy.get('[data-cy-session="time"]').contains(session.time);
    cy.get('[data-cy-session="time"]').contains(tomorrow);
    cy.get('[data-cy-session="room"]').contains(session.venue_room);
    cy.get('[data-cy="session-video"]').find('iframe').should('be.visible');
    cy.get('#session-modal').find('a.modal__close').click();
    cy.wait(1000);

    cy.get('[data-cy="session-title"]').contains(proposal.title).click();
    cy.wait('@view-session');
    cy.get('[data-cy-session="title"]').contains(proposal.title);
    cy.get('[data-cy-session="speaker"]').contains(user.username);
    cy.get('[data-cy-session="time"]').contains(tomorrow);
    cy.get('[data-cy-session="room"]').contains(proposal.venue_room);
    cy.get('[data-cy="view-proposal"]').should('have.exist');
    cy.get('[data-cy="view-proposal"]').invoke('removeAttr', 'target').click();
    cy.get('a[data-cy="proposal-menu"]:visible').should('not.exist');
  });
});
