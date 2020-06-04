describe('Add a new proposal', function() {
  const user = require('../fixtures/user.json').user;
  const profile = require('../fixtures/profile.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');
  const labels = require('../fixtures/labels.json');

  it('Add proposal', function() {
    cy.login('/' + profile.title, user.username, user.password);

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
    cy.get('#field-video_url').type(proposal.preview_video);
    cy.get('#field-bio')
      .find('.CodeMirror textarea')
      .type(proposal.speaker_bio, { force: true });
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
    cy.get('[data-cy="proposal-video"]')
      .find('iframe')
      .should('be.visible');
    cy.get('[data-cy-admin="edit"]').should('exist');
    cy.get('[data-cy-admin="delete"]').should('exist');
    cy.get('[data-cy="edit-proposal-video"]').should('exist');

    cy.get('#field-comment_message')
      .find('.CodeMirror textarea')
      .type(proposal.proposer_note, { force: true });
    cy.get('#comment-form').submit();
    cy.get('.comment--body').contains(proposal.proposer_note);
    cy.get('.comment--header').contains(user.username);
  });
});
