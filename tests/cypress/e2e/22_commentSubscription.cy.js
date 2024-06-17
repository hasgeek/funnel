/* eslint-disable global-require */
describe('Confirm submission comment subscription', () => {
  const { editor, newuser } = require('../fixtures/user.json');
  const member = require('../fixtures/user.json').user;
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');

  it('Confirm proposal', () => {
    cy.server();
    cy.route('POST', '**/new').as('post-comment');
    cy.route('POST', '**/subscribe').as('post-subscribe');
    cy.route('GET', '**/updates?*').as('fetch-updates');

    cy.login('/', member.username, member.password);
    cy.get('#hgnav').find('a[data-testid="my-account"]').click();
    cy.wait(1000);
    cy.get('a[data-testid="profile"]').click();
    cy.get('a[data-testid="submissions"]').click();
    cy.get(`a[data-testid="${proposal.title}"]`).click();
    cy.get('[data-testid="post-comment"]').click();
    cy.get('[data-testid="new-form"]')
      .find('.cm-editor .cm-line')
      .type(proposal.comment_2, { force: true });
    cy.wait(1000);
    cy.get('[data-testid="new-form"]').find('[data-testid="submit-comment"]').click();
    cy.wait('@post-comment');
    cy.visit('/');
    cy.logout();
    cy.wait(1000);

    cy.login('/', editor.username, editor.password);
    cy.get('a[data-testid="my-updates"]:visible').click();
    cy.wait('@fetch-updates');
    cy.get('[data-testid="notification-box"]').contains(project.title);
    cy.get('[data-testid="notification-box"]').contains(proposal.title);
    cy.get('[data-testid="comment-sidebar"]').click();
    cy.wait(1000);
    cy.get('[data-testid="unread-comment"]').contains(project.reply_comment);
    cy.get('[data-testid="unread-comment"]').contains(proposal.comment_2);
    cy.logout();
    cy.wait(1000);

    cy.login('/', newuser.username, newuser.password);
    cy.get('[data-testid="comment-sidebar"]').click();
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('a[data-testid="submissions"]').click();
    cy.get('#header-search').type(proposal.title);
    cy.get(`a[data-testid="${proposal.title}"]`).click();
    cy.get('a[data-testid="subscribe-proposal"]:visible').click();
    cy.wait(1000);
    cy.get('[data-testid="subscription"]:visible').click();
    cy.wait('@post-subscribe');
    cy.get('a[data-testid="subscribe-proposal"]:visible').click();
    cy.wait(1000);
    cy.get('[data-testid="cancel-subscription"]:visible').click();
    cy.wait('@post-subscribe');
    cy.get('a[data-testid="subscribe-proposal"]:visible').click();
    cy.wait(1000);
    cy.get('[data-testid="subscription"]:visible').click();
    cy.wait('@post-subscribe');
    cy.visit('/');
    cy.logout();
    cy.wait(1000);

    cy.login('/', member.username, member.password);
    cy.get('a[data-testid="my-account"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="profile"]').click();
    cy.get('a[data-testid="submissions"]').click();
    cy.get(`a[data-testid="${proposal.title}"]`).click();
    cy.get('[data-testid="post-comment"]').click();
    cy.get('[data-testid="new-form"]')
      .find('.cm-editor .cm-line')
      .type(proposal.comment_3, { force: true });
    cy.wait(1000);
    cy.get('[data-testid="new-form"]').find('[data-testid="submit-comment"]').click();
    cy.wait('@post-comment');
    cy.visit('/');
    cy.logout();
    cy.wait(1000);
  });
});
