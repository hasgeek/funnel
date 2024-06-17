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
    cy.get('[data-testid="schedule"]').click();

    cy.get('a[data-testid="add-to-calendar"]').click();
    cy.wait(1000);
    cy.get('[data-testid="schedule-subscribe"]').should('exist');
    cy.get('a[data-testid="close-modal"]').click();

    let tomorrow = dayjs().add(1, 'days').format('dddd, D MMMM YYYY');
    cy.get('.schedule__date').contains(tomorrow);
    cy.fixture('venues').then((venues) => {
      venues.forEach((venue) => {
        cy.get('.schedule__row__column--header').contains(venue.room.title);
      });
    });
    cy.get('[data-testid="session-time"]').contains(session.time).click();
    cy.wait('@view-session');
    cy.get('#session-modal').should('be.visible');
    tomorrow = dayjs().add(1, 'days').format('MMM D, YYYY');
    cy.get('[data-testid="title"]').contains(session.title);
    cy.get('[data-testid="speaker"]').contains(session.speaker);
    cy.get('[data-testid="time"]').contains(session.time);
    cy.get('[data-testid="time"]').contains(tomorrow);
    cy.get('[data-testid="room"]').contains(session.venue_room);
    cy.get('[data-testid="session-video"]').find('iframe').should('be.visible');
    cy.get('#session-modal').find('a.modal__close').click();
    cy.wait(1000);

    cy.get('[data-testid="session-title"]').contains(proposal.title).click();
    cy.wait('@view-session');
    cy.get('[data-testid="title"]').contains(proposal.title);
    cy.get('[data-testid="speaker"]').contains(user.fullname);
    cy.get('[data-testid="time"]').contains(tomorrow);
    cy.get('[data-testid="room"]').contains(proposal.venue_room);
    cy.get('[data-testid="view-proposal"]').should('have.exist');
    cy.get('[data-testid="view-proposal"]').invoke('removeAttr', 'target').click();
    cy.get('a[data-testid="proposal-menu"]:visible').should('not.exist');
  });
});
