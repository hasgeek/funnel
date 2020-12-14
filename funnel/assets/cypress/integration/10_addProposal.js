describe('Add a new proposal', function () {
  const user = require('../fixtures/user.json').user;
  const editor = require('../fixtures/user.json').editor;
  const profile = require('../fixtures/profile.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');
  const labels = require('../fixtures/labels.json');

  it('Add proposal', function () {
    cy.server();
    cy.route('GET', '**/admin').as('fetch-admin-panel');
    cy.route('GET', '**/updates/*').as('fetch-updates');
    cy.route('POST', '**/new').as('post-comment');

    cy.login('/' + profile.title, user.username, user.password);

    cy.get('a[data-cy-title="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="submissions"]').click();
    cy.location('pathname').should('contain', 'proposals');
    cy.get('a[data-cy="propose-a-session"]').click();
    cy.location('pathname').should('contain', 'new');
    cy.get('#title').type(proposal.title);
    cy.get('#field-body')
      .find('.CodeMirror textarea')
      .type(proposal.content, { force: true });
    cy.get('#field-video_url').type(proposal.preview_video);
    cy.get('fieldset').find('.listwidget').eq(0).find('input').eq(0).click();
    cy.get('fieldset').find('.listwidget').eq(1).find('input').eq(0).click();
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.location('pathname').should('contain', 'proposals');

    cy.get('[data-cy="proposal-title"]')
      .should('exist')
      .contains(proposal.title);
    cy.get('[data-cy="proposal-video"]').find('iframe').should('be.visible');
    cy.get('.proposal__section').find('a[data-cy="admin-panel"]').click();
    cy.wait('@fetch-admin-panel');
    cy.get('[data-cy-admin="edit"]').should('exist');
    cy.get('[data-cy-admin="delete"]').should('exist');
    cy.get('[data-cy="edit-proposal-video"]').should('exist');

    cy.get('a[data-cy="close-admin-panel"]').click();
    cy.get('[data-cy="post-comment"]').click();
    cy.get('[data-cy="new-form"]')
      .find('.CodeMirror textarea')
      .type(proposal.proposer_note, { force: true });
    cy.wait(1000);
    cy.get('[data-cy="new-form"]').find('[data-cy="submit-comment"]').click();
    cy.wait('@post-comment');
    cy.get('.comment__body').contains(proposal.proposer_note);
    cy.get('.comment__header').contains(user.username);

    cy.visit('/');
    cy.logout();
    cy.wait(1000);
    cy.login('/' + profile.title, editor.username, editor.password);
    cy.visit('/updates');
    cy.wait('@fetch-updates');
    cy.get('[data-cy="notification-box"]').contains(proposal.title);
  });
});
