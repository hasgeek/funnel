/* eslint-disable global-require */
describe('Test comments feature', () => {
  const { user, hguser, editor } = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');

  it('Post comment on project page', () => {
    cy.server();
    cy.route('GET', '**/new').as('get-form');
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
    cy.get('a[data-testid="comments"]').click();
    cy.wait(2000);
    cy.get('a[data-testid="login-btn"]').click();
    cy.fill_login_details(user.username, user.password);
    cy.wait(2000);
    cy.get('[data-testid="post-comment"]').click();
    cy.get('[data-testid="new-form"]')
      .find('.cm-editor .cm-line')
      .type(project.comment, { force: true });
    cy.wait(1000);
    cy.get('[data-testid="new-form"]').find('[data-testid="submit-comment"]').click();
    cy.wait('@post-comment');
    let cid = window.location.hash;
    cy.get('.comment__body').contains(project.comment);
    cy.get('.comment__header').contains(user.username);

    cy.wait(2000);
    cy.get('a[data-testid="comment-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="edit"]').click();
    cy.get('[data-testid="edit-form"]')
      .find('.cm-editor .cm-line')
      .type(project.edit_comment, { force: true });
    cy.wait(1000);
    cy.get('[data-testid="edit-form"]').find('[data-testid="edit-comment"]').click();
    cy.wait('@edit-comment');
    cy.get(`${cid} .comment__body`).contains(project.edit_comment);

    cy.get('a[data-testid="reply"]').click();
    cy.get('[data-testid="reply-form"]')
      .find('.cm-editor .cm-line')
      .type(project.reply_comment, { force: true });
    cy.wait(1000);
    cy.get('[data-testid="reply-form"]').find('[data-testid="reply-comment"]').click();
    cy.wait('@reply-comment');
    cid = window.location.hash;
    cy.get(`${cid} .comment__body`).contains(project.reply_comment);
    cy.wait(2000);
    cy.get('[data-testid="comment-sidebar"]').click();
    cy.wait(2000);
    cy.get('[data-testid="unread-comment"]').should('exist');

    /*
    The test for deleting comments has been disabled as it
    interferes with the comment notification test. To be added back later.
    cy.get('a[data-testid="comment-menu"]:visible').eq(1).click();
    cy.wait(1000);
    cy.get('a[data-testid="delete"]:visible').click();
    cy.wait(1000);
    cy.get('button[data-testid="confirm-delete-btn"]').click();
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
    cy.get('a[data-testid="comments"]').click();
    cy.get('[data-testid="post-comment"]').should('exist');
  });
});
