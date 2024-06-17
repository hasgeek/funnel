describe('Setup ticketed event for checkin', () => {
  const { promoter } = require('../../fixtures/user.json');
  const project = require('../../fixtures/project.json');

  it('Setup ticketed event for checkin', () => {
    cy.login('/', promoter.username, promoter.password);

    cy.get(`[data-testid="${project.title}"]`).first().click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-testid="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-testid="setup-ticket-events"').click();
    cy.location('pathname').should('contain', '/admin');

    cy.fixture('ticket_events').then((ticketEvents) => {
      ticketEvents.forEach((ticketEvent) => {
        cy.get('a[data-testid="new-ticket-event"]').click();
        cy.get('#title').type(ticketEvent.title);
        cy.get('#badge_template').type(ticketEvent.badge_template);
        cy.get('button[data-testid="form-submit-btn"]').click();
      });
    });
  });
});
