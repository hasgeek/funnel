describe('Add session to schedule and publish', function() {
  const { admin } = require('../fixtures/user.js');
  const session = require('../fixtures/session.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');

  it('Update schedule', function() {
    cy.server();
    cy.route('**/sessions/new').as('add-session');

    cy.relogin('/testcypressproject');
    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="edit-schedule"').click();
    cy.location('pathname').should('contain', 'schedule');
    var tomorrow = Cypress.moment()
      .add(1, 'days')
      .format('YYYY-MM-DD');
    cy.wait(60000);
    cy.get('#select-date')
      .type(tomorrow)
      .click();
    cy.get('.js-unscheduled').click();
    cy.get('.fc-agenda-axis')
      .contains(session.timecolumn)
      .next('.fc-widget-content')
      .click(5, 5);
    cy.get('#popup').should('be.visible');
    cy.get('#title').type(session.title);
    cy.get('select#venue_room_id').select(session.room, { force: true });
    cy.get('#field-speaker').type(session.speaker);
    cy.get('#field-banner_image_url').type(session.bg);
    cy.get('#field-is_break')
      .find('label')
      .click();
    cy.get('#session-save').click();
    cy.wait('@add-session');

    cy.get('[data-cy="project-page"]').click();
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('button[data-cy-schedule=publish_schedule]').click();
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('[data-cy="schedule-state"]').contains('Upcoming');

    cy.get('a[data-cy="home-desktop"]').click();
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title);
  });
});
