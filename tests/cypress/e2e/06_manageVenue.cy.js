/* eslint-disable global-require */
describe('Manage project venue', () => {
  const { editor } = require('../fixtures/user.json');
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  it('Add venue', () => {
    cy.login(
      `/${profile.title}/${project.url}`,
      editor.username,
      editor.password
    );

    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-navbar="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="manage-venues"]').click();
    cy.location('pathname').should('contain', '/venues');

    cy.fixture('venues').then((venues) => {
      venues.forEach((venue) => {
        cy.get('a[data-cy="new-venue"]').click();
        cy.location('pathname').should('contain', '/new');
        cy.get('#title').type(venue.venue_title);
        cy.get('#field-description')
          .find('.cm-editor .cm-line')
          .type(venue.venue_description, { force: true });
        cy.get('#address1').type(venue.venue_address1);
        cy.get('#address2').type(venue.venue_address2);
        cy.get('#city').type(venue.venue_city);
        cy.get('#state').type(venue.venue_state);
        cy.get('#postcode').type(venue.venue_postcode);
        cy.get('button[data-cy="form-submit-btn"]').click();
        cy.location('pathname').should(
          'include',
          `/testcypressproject/${project.url}/venues`
        );
      });

      cy.get(`[data-cy="${venues[1].venue_title}"]`).click();
      cy.get('[data-cy="set-primary-venue"]').click();
      cy.get(`[data-cy="${venues[1].venue_title}"]`)
        .find('em')
        .contains('(primary)');

      venues.forEach((venue) => {
        cy.get(`.card[data-cy-venue="${venue.venue_title}"]`)
          .find('a[data-cy="add-room"]')
          .click();
        cy.location('pathname').should('contain', '/new');
        cy.get('#title').type(venue.room.title);
        cy.get('#field-description')
          .find('.cm-editor .cm-line')
          .type(venue.room.description, { force: true });
        cy.get('#bgcolor').clear().type(venue.room.bgcolor);
        cy.get('button[data-cy="form-submit-btn"]').click();
        cy.location('pathname').should(
          'include',
          `/testcypressproject/${project.url}/venues`
        );
        cy.get(`.card[data-cy-venue="${venue.venue_title}"]`)
          .find('li')
          .contains(venue.room.title);
      });

      venues.forEach((venue) => {
        cy.get(`[data-cy-room="${venue.room.title}"]`).should('exist');
      });
    });
  });
});
