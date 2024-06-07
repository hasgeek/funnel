import { user, hguser } from '../fixtures/user.json';
import project from '../fixtures/project.json';

describe('Test comments feature', () => {
  it('Post comment on project page', () => {
    cy.intercept('GET', '**/new').as('get-form');
    cy.intercept('POST', '**/new').as('post-comment');
    cy.intercept('POST', '**/edit').as('edit-comment');
    cy.intercept('POST', '**/reply').as('reply-comment');
    cy.intercept('POST', '**/delete').as('delete-comment');
    cy.intercept('**/json').as('edit-comment');

    cy.visit('/');
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="comments"]').click();
    cy.wait(2000);
    cy.get('a[data-cy="login-btn"]').click();
    cy.fill_login_details(user.username, user.password);
    cy.wait(2000);
    cy.get('[data-cy="post-comment"]').click();
    cy.get('[data-cy="new-form"]')
      .find('.cm-editor .cm-line')
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
      .find('.cm-editor .cm-line')
      .type(project.edit_comment, { force: true });
    cy.wait(1000);
    cy.get('[data-cy="edit-form"]').find('[data-cy="edit-comment"]').click();
    cy.wait('@edit-comment');
    cy.get(`${cid} .comment__body`).contains(project.edit_comment);

    cy.get('a[data-cy="reply"]').click();
    cy.get('[data-cy="reply-form"]')
      .find('.cm-editor .cm-line')
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
  });
});
