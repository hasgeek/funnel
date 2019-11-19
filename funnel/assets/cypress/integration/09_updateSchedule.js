describe('Project', function() {
  const admin = require('../fixtures/admin.json');
  const session = require('../fixtures/session.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');

  it('Update schedule', function() {
    cy.visit('/')
      .get('#hgnav')
      .find('.header__button')
      .click();
    cy.get('#showmore').click();
    cy.get('.field-username')
      .type(admin.username)
      .should('have.value', admin.username);
    cy.get('.field-password')
      .type(admin.password)
      .should('have.value', admin.password);
    cy.get('.form-actions')
      .find('button')
      .click();

    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.wait(1000);
    cy.get('a[data-cy="schedule"').click();
    cy.wait(1000);
    var today = Cypress.moment()
      .add(1, 'days')
      .format('YYYY-MM-DD');
    cy.get('#select-date')
      .type(today)
      .trigger('change');
    cy.contains('.fc-widget-header', '9am')
      .next('.fc-widget-content')
      .click(5, 5);
    cy.get('#title').type(session.title);
    cy.get('select#venue_room_id').select(session.room, { force: true });
    cy.get('#field-banner_image_url').type(session.bg);
    cy.get('#field-is_break')
      .find('label')
      .click();
    cy.get('#session-save').click();
    cy.wait(1000);
    cy.get('[data-cy="project-page"]').click();
    cy.get('button[data-cy-schedule=publish_schedule]').click();
    cy.wait(1000);
    cy.get('[data-cy="schedule-state"]').contains('Upcoming');

    cy.get('.header__site-title__title')
      .find('a')
      .click();
    cy.wait(1000);
    cy.get('.upcoming')
      .find('li.card--upcoming')
      .contains(project.title);

    // cy.contains('.fc-widget-header', '9:10am').scrollIntoView();
    // cy.get('.js-unscheduled')
    //   .trigger('mousedown', { which: 1 })
    //   .trigger('mousemove', { which: 1, pageX: 410, pageY: 130 })
    //   .trigger('mouseup', { which: 1, force: true });
  });
});
