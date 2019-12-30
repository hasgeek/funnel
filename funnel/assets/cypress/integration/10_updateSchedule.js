describe('Project', function() {
  const { admin } = require('../fixtures/user.js');
  const session = require('../fixtures/session.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');

  it('Update schedule', function() {
    cy.server();
    cy.route('**/sessions/new').as('add-session');

    cy.relogin('/testcypressproject/');
    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);

    cy.get('a[data-cy="schedule"').click();
    cy.location('pathname').should('contain', 'schedule');
    var tomorrow = Cypress.moment()
      .add(1, 'days')
      .format('YYYY-MM-DD');
    cy.get('#select-date')
      .type(tomorrow)
      .click();
    cy.get('.js-unscheduled').click();
    cy.get('.fc-agenda-axis')
      .contains(session.time)
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
    cy.get('button[data-cy-schedule=publish_schedule]').click();
    cy.get('[data-cy="schedule-state"]').contains('Upcoming');

    cy.get('.header__site-title__title')
      .find('a')
      .click();
    cy.get('.upcoming')
      .find('li.card--upcoming')
      .contains(project.title);

    // cy.get('.js-unscheduled').then(el => {
    //   const draggable = el[0]; // Pick up this
    //   console.log('draggable', draggable);
    //   cy.get('.fc-slot120 .fc-widget-content').then(el => {
    //     const droppable = el[0]; // Drop over this
    //     console.log('droppable', droppable);

    //     const coords = droppable.getBoundingClientRect();
    //     console.log('coords', coords);
    //     el.trigger('mousemove');
    //     el.trigger('mousedown');
    //     el.trigger('mousemove', { clientX: 10, clientY: 0 });
    //     el.trigger('mousemove', {
    //       clientX: 30,
    //       clientY: 429,
    //     });
    //     el.trigger('mouseup');
    //   });
    // });
    // cy.get('.js-unscheduled')
    //   .trigger('mouseover', { which: 1, force: true, view: window })
    //   .trigger('mousedown', { which: 1, force: true, view: window })
    //   .trigger('mousemove', {
    //     pageX: 230,
    //     pageY: 429,
    //     force: true,
    //     view: window,
    //   })
    //   .trigger('mouseup', { force: true, view: window });
    // const eventData = {
    //   date: new Date(),
    //   dateStr: new Date().toISOString(),
    //   draggedEl: {
    //     dataset: {
    //       notificationId: '123',
    //       priority: '0',
    //       title: 'Test',
    //     },
    //   },
    //   jsEvent: null,
    //   resource: {
    //     id: '123',
    //   },
    //   event: null,
    //   oldEvent: null,
    // };

    // cy.get('.fc-slot120 td.fc-widget-content').scrollIntoView();

    // cy.get('.js-unscheduled') // selector for the external event I want to drag in the calendar
    //   .trigger('dragstart')
    //   .get('.fc-slot120 td.fc-widget-content') // selector for where I want to drop the event.
    //   .trigger('drop', eventData); // this will fire the eventDrop event
    // cy.wait(1000);
  });
});
