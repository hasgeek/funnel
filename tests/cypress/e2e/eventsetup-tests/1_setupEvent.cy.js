import { promoter } from '../../fixtures/user.json';
import project from '../../fixtures/project.json';

describe('Setup ticketed event for checkin', () => {
  it('Setup ticketed event for checkin', () => {
    cy.login('/', promoter.username, promoter.password);

    cy.get(`[data-cy-title="${project.title}"]`).first().click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-navbar="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="setup-ticket-events"').click();
    cy.location('pathname').should('contain', '/admin');

    cy.fixture('ticket_events').then((ticketEvents) => {
      ticketEvents.forEach((ticketEvent) => {
        cy.get('a[data-cy="new-ticket-event"]').click();
        cy.get('#title').type(ticketEvent.title);
        cy.get('#badge_template').type(ticketEvent.badge_template);
        cy.get('button[data-cy="form-submit-btn"]').click();
      });
    });
  });
});
