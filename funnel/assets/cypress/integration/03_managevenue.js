describe('Project', function() {
  const user = require('../../fixtures/user.json');

  it('Publish project', function() {
    cy.visit('/JSFoo/' + project.url)
      .get('#hgnav')
      .find('.header__button')
      .click();
    cy.get('#showmore').click();
    cy.get('.field-username')
      .type(user.username)
      .should('have.value', user.username);
    cy.get('.field-password')
      .type(user.password)
      .should('have.value', user.password);
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
      cy.get('[data-cy="' + venues[1].venue_title + '"]')
        .find('em')
        .contains('(primary)');
      cy.get('.card[data-cy-venue="' + venues[1].venue_title + '"]')
        .find('a')
        .click();
      cy.wait(500);
      cy.get('#title').type(venues[1].room.title);
      cy.get('#field-description')
        .find('.CodeMirror textarea')
        .type(venues[1].room.description, { force: true });
      cy.get('#bgcolor')
        .clear()
        .type(venues[1].room.bgcolor);
      cy.contains('Create').click();
      cy.wait(500);
      cy.get('.card[data-cy-venue="' + venues[1].venue_title + '"]')
        .find('li')
        .contains(venues[1].room.title);
    });
  });
});
