describe('Add a new proposal', function() {
  const user = require('../fixtures/user.json').user;
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');
  const labels = require('../fixtures/labels.json');

  it('Add proposal', function() {
    cy.login('/testcypressproject', user.username, user.password);

    cy.get('a[data-cy-project="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="proposals"]').click();
    cy.location('pathname').should('contain', 'proposals');
    cy.get('a[data-cy="propose-a-session"]').click();
    cy.location('pathname').should('contain', 'new');
    cy.get('#speaking label')
      .eq(0)
      .click();
    cy.get('#title').type(proposal.title);
    cy.get('#field-abstract')
      .find('.CodeMirror textarea')
      .type(proposal.abstract, { force: true });
    cy.get('#field-outline')
      .find('.CodeMirror textarea')
      .type(proposal.outline, { force: true });
    cy.get('#slides').type(proposal.slides);
    cy.get('#preview_video').type(proposal.preview_video);
    cy.get('#field-bio')
      .find('.CodeMirror textarea')
      .type(proposal.speaker_bio, { force: true });
    cy.get('#email').type(proposal.email);
    cy.get('#phone').type(proposal.phone);
    cy.get('#location').type(proposal.location);
    cy.get('fieldset')
      .find('.listwidget')
      .eq(0)
      .find('input')
      .eq(0)
      .click();
    cy.get('fieldset')
      .find('.listwidget')
      .eq(1)
      .find('input')
      .eq(0)
      .click();
    cy.get('button')
      .contains('Submit proposal')
      .click();
    cy.location('pathname').should('contain', 'proposals');

    cy.get('.proposal__section__headline')
      .should('exist')
      .contains(proposal.title);
    cy.get('[data-cy-admin="edit"]').should('exist');
    cy.get('[data-cy-admin="delete"]').should('exist');
  });
});
