describe('Confirm submission comment subscription', function () {
  const editor = require('../fixtures/user.json').editor;
  const member = require('../fixtures/user.json').user;
  const profile = require('../fixtures/profile.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');

  it('Confirm proposal', function () {
    cy.server();
    cy.route('POST', '**/new').as('post-comment');
    cy.route('POST', '**/subscribe').as('post-subscribe');

    cy.login('/', member.username, member.password);
    cy.get('a[data-cy="profile"]').click();
    cy.get('a[data-cy="submissions"]').click();
    cy.get('a[data-cy-proposal="' + proposal.title + '"]').click();
    cy.get('[data-cy="post-comment"]').click();
    cy.get('[data-cy="new-form"]')
      .find('.CodeMirror textarea')
      .type(proposal.comment_2, { force: true });
    cy.wait(1000);
    cy.get('[data-cy="new-form"]').find('[data-cy="submit-comment"]').click();
    cy.wait('@post-comment');
    cy.visit('/');
    cy.logout();
    cy.wait(1000);

    cy.login('/', editor.username, editor.password);
    cy.get('[data-cy="comment-sidebar"]').click();
    cy.wait(1000);
    cy.get('[data-cy="unread-comment"]').should('exist');
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('a[data-cy-navbar="submissions"]').click();
    cy.get('#search').type(proposal.title);
    cy.get('a[data-cy-proposal="' + proposal.title + '"]').click();
    cy.get('a[data-cy="subscribe-proposal"]:visible').click();
    cy.wait(1000);
    cy.get('[data-cy="cancel-subscription"]:visible').click();
    cy.wait('@post-subscribe');
    cy.visit('/');
    cy.logout();
    cy.wait(1000);

    cy.login('/', member.username, member.password);
    cy.get('a[data-cy="profile"]').click();
    cy.get('a[data-cy="submissions"]').click();
    cy.get('a[data-cy-proposal="' + proposal.title + '"]').click();
    cy.get('[data-cy="post-comment"]').click();
    cy.get('[data-cy="new-form"]')
      .find('.CodeMirror textarea')
      .type(proposal.comment_3, { force: true });
    cy.wait(1000);
    cy.get('[data-cy="new-form"]').find('[data-cy="submit-comment"]').click();
    cy.wait('@post-comment');
    cy.visit('/');
    cy.logout();
    cy.wait(1000);

    cy.login('/', editor.username, editor.password);
    cy.get('[data-cy="comment-sidebar"]').click();
    cy.wait(1000);
    cy.get('[data-cy="unread-comment"]')
      .contains(member.username)
      .should('not.exist');
  });
});
