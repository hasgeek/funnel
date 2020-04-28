describe('Add session to schedule and publish', function() {
  const editor = require('../fixtures/user.json').editor;
  const session = require('../fixtures/session.json');
  const proposal = require('../fixtures/proposal.json');
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  it('Update schedule', function() {
    cy.server();
    cy.route('**/sessions/new').as('new-session-form');
    cy.route('POST', '**/sessions/new').as('add-new-session');
    cy.route('**/schedule').as('session-form');
    cy.route('POST', '**/schedule').as('add-session');

    cy.login('/' + profile.title, editor.username, editor.password);

    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="edit-schedule"').click();
    cy.location('pathname').should('contain', 'schedule');
    var tomorrow = Cypress.moment()
      .add(1, 'days')
      .format('YYYY-MM-DD');
    cy.get('#select-date')
      .type(tomorrow)
      .click();
    cy.get('.js-unscheduled').click();
    cy.get('.fc-agenda-axis')
      .contains(session.timecolumn)
      .next('.fc-widget-content')
      .click(5, 5);
    cy.wait('@new-session-form');
    cy.get('#popup').should('be.visible');
    cy.get('#title').type(session.title);
    cy.get('select#venue_room_id').select(session.room, { force: true });
    cy.get('#field-speaker').type(session.speaker);
    cy.get('#field-banner_image_url').type(session.bg);
    cy.get('#field-is_break')
      .find('label')
      .click();
    cy.get('#field-video_url').type(session.video);
    cy.get('#session-save').click();
    cy.wait('@add-new-session');

    cy.get('.js-unscheduled')
      .trigger('mousedown', { which: 1 })
      .trigger('mousemove', { pageX: 230, pageY: 550 })
      .trigger('mousemove', { pageX: 230, pageY: 570 })
      .trigger('mouseup', { force: true });
    cy.wait('@session-form');
    cy.get('select#venue_room_id').select(proposal.room, { force: true });
    cy.get('#session-save').click();
    cy.wait('@add-session');

    cy.get('[data-cy-tab="settings"]').click();
    cy.get('[data-cy-collapsible="open"]')
      .eq(0)
      .click();
    cy.get('.sp-dd')
      .eq(0)
      .click();
    cy.get('.sp-palette-container').should('exist');

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
