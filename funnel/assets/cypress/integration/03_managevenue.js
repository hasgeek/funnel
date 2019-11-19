describe('Project', function() {
  const admin = require('../fixtures/admin.json');
  const project = require('../fixtures/project.json');

  it('Add venue', function() {
    cy.visit('/JSFoo/' + project.url)
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

    cy.get('a[data-cy="manage-venues"]').click();
    cy.wait(500);

    cy.fixture('venues').then(venues => {
      venues.forEach(function(venue) {
        cy.get('a[data-cy="new-venue"]').click();
        cy.wait(500);
        console.log('venue', venue);
        cy.get('#title').type(venue.venue_title);
        cy.get('#field-description')
          .find('.CodeMirror textarea')
          .type(venue.venue_description, { force: true });
        cy.get('#address1').type(venue.venue_address1);
        cy.get('#address2').type(venue.venue_address2);
        cy.get('#city').type(venue.venue_city);
        cy.get('#state').type(venue.venue_state);
        cy.get('#postcode').type(venue.venue_postcode);
        cy.contains('Add venue').click();
        cy.wait(500);
      });

      cy.get('[data-cy="' + venues[1].venue_title + '"]').click();
      cy.get('[data-cy="set-primary-venue"]').click();
      cy.get('[data-cy="' + venue.venue_title + '"]')
        .find('em')
        .contains('(primary)');

      venues.forEach(function(venue) {
        cy.get('.card[data-cy-venue="' + venue.venue_title + '"]')
          .find('a[data-cy="add-room"]')
          .click();
        cy.wait(500);
        cy.get('#title').type(venue.room.title);
        cy.get('#field-description')
          .find('.CodeMirror textarea')
          .type(venue.room.description, { force: true });
        cy.get('#bgcolor')
          .clear()
          .type(venue.room.bgcolor);
        cy.contains('Create').click();
        cy.wait(500);
        cy.get('.card[data-cy-venue="' + venue.venue_title + '"]')
          .find('li')
          .contains(venue.room.title);
      });

      venues.forEach(function(venue) {
        cy.get('[data-cy-room="' + venue.room.title + '"]').should('exist');
      });
    });
  });
});
