describe('Manage project venue', function () {
  const editor = require('../fixtures/user.json').editor;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  it('Add venue', function () {
    cy.login(
      '/' + profile.title + '/' + project.url,
      editor.username,
      editor.password
    );

    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="manage-venues"]').click();
    cy.location('pathname').should('contain', '/venues');

    cy.fixture('venues').then((venues) => {
      venues.forEach(function (venue) {
        cy.get('a[data-cy="new-venue"]').click();
        cy.location('pathname').should('contain', '/new');
        cy.get('#title').type(venue.venue_title);
        cy.get('#field-description')
          .find('.CodeMirror textarea')
          .type(venue.venue_description, { force: true });
        cy.get('#address1').type(venue.venue_address1);
        cy.get('#address2').type(venue.venue_address2);
        cy.get('#city').type(venue.venue_city);
        cy.get('#state').type(venue.venue_state);
        cy.get('#postcode').type(venue.venue_postcode);
        cy.get('button').contains('Add venue').click();
        cy.location('pathname').should(
          'include',
          '/testcypressproject/' + project.url + '/venues'
        );
      });

      cy.get('[data-cy="' + venues[1].venue_title + '"]').click();
      cy.get('[data-cy="set-primary-venue"]').click();
      cy.get('[data-cy="' + venues[1].venue_title + '"]')
        .find('em')
        .contains('(primary)');

      venues.forEach(function (venue) {
        cy.get('.card[data-cy-venue="' + venue.venue_title + '"]')
          .find('a[data-cy="add-room"]')
          .click();
        cy.location('pathname').should('contain', '/new');
        cy.get('#title').type(venue.room.title);
        cy.get('#field-description')
          .find('.CodeMirror textarea')
          .type(venue.room.description, { force: true });
        cy.get('#bgcolor').clear().type(venue.room.bgcolor);
        cy.get('button').contains('Create').click();
        cy.location('pathname').should(
          'include',
          '/testcypressproject/' + project.url + '/venues'
        );
        cy.get('.card[data-cy-venue="' + venue.venue_title + '"]')
          .find('li')
          .contains(venue.room.title);
      });

      venues.forEach(function (venue) {
        cy.get('[data-cy-room="' + venue.room.title + '"]').should('exist');
      });
    });
  });
});
