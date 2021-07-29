/* eslint-disable global-require */
describe('Test comments feature', () => {
  const { user, hguser, editor } = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');

  it('Post comment on project page', () => {
    cy.server();
    cy.route('GET', '**/new').as('get-form');
    cy.route('GET', '**/updates?*').as('fetch-updates');
    cy.route('POST', '**/new').as('post-comment');
    cy.route('POST', '**/edit').as('edit-comment');
    cy.route('POST', '**/reply').as('reply-comment');
    cy.route('POST', '**/delete').as('delete-comment');
    cy.route('**/json').as('edit-comment');

    cy.visit('/');
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="comments"]').click();
    cy.get('a[data-cy="login-btn"]').click();
    cy.fill_login_details(user.username, user.password);

    cy.get('[data-cy="post-comment"]').click();
    cy.get('[data-cy="new-form"]')
      .find('.CodeMirror textarea')
      .type(project.comment, { force: true });
    cy.wait(1000);
    cy.get('[data-cy="new-form"]').find('[data-cy="submit-comment"]').click();
    cy.wait('@post-comment');
    let cid = window.location.hash;
    cy.get('.comment__body').contains(project.comment);
    cy.get('.comment__header').contains(user.username);

    cy.wait(2000);
    cy.get('a[data-cy="comment-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy="edit"]').click();
    cy.get('[data-cy="edit-form"]')
      .find('.CodeMirror textarea')
      .type(project.edit_comment, { force: true });
    cy.wait(1000);
    cy.get('[data-cy="edit-form"]').find('[data-cy="edit-comment"]').click();
    cy.wait('@edit-comment');
    cy.get(`${cid} .comment__body`).contains(project.edit_comment);

    cy.get('a[data-cy="reply"]').click();
    cy.get('[data-cy="reply-form"]')
      .find('.CodeMirror textarea')
      .type(project.reply_comment, { force: true });
    cy.wait(1000);
    cy.get('[data-cy="reply-form"]').find('[data-cy="reply-comment"]').click();
    cy.wait('@reply-comment');
    cid = window.location.hash;
    cy.get(`${cid} .comment__body`).contains(project.reply_comment);
    cy.wait(2000);
    cy.get('[data-cy="comment-sidebar"]').click();
    cy.wait(2000);
    cy.get('[data-cy="unread-comment"]').should('exist');

    /*
    The test for deleting comments has been disabled as it
    interferes with the comment notification test. To be added back later.
    cy.get('a[data-cy="comment-menu"]:visible').eq(1).click();
    cy.wait(1000);
    cy.get('a[data-cy="delete"]:visible').click();
    cy.wait(1000);
    cy.get('button[data-cy="confirm-delete-btn"]').click();
    cy.wait('@delete-comment');
    cy.get('.comment__body')
      .contains(project.reply_comment)
      .should('not.exist');
    cy.wait(5000);
     */

    cy.logout();

    cy.login('/', hguser.username, hguser.password);
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="comments"]').click();
    cy.get('[data-cy="post-comment"]').should('exist');

    cy.logout();
    cy.login('/', editor.username, editor.password);
    cy.get('a[data-cy="my-updates"]:visible').click();
    cy.wait('@fetch-updates');
    cy.get('[data-cy="notification-box"]').contains(project.title);
    cy.get('[data-cy="comment-sidebar"]').click();
    cy.wait(2000);
    cy.get('[data-cy="unread-comment"]').should('exist');
  });
});
