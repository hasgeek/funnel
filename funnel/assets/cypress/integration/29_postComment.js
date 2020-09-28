describe('Test comments feature', function () {
  const user = require('../fixtures/user.json').user;
  const hguser = require('../fixtures/user.json').hguser;
  const editor = require('../fixtures/user.json').editor;
  const project = require('../fixtures/project.json');

  it('Post comment on project page', function () {
    cy.server();
    cy.route('GET', '**/new').as('get-form');
    cy.route('GET', '**/updates/*').as('fetch-updates');
    cy.route('POST', '**/new').as('post-comment');
    cy.route('GET', '**/edit').as('edit-form');
    cy.route('POST', '**/edit').as('edit-comment');
    cy.route('GET', '**/reply').as('reply-form');
    cy.route('POST', '**/reply').as('reply-comment');
    cy.route('GET', '**/delete').as('delete-form');
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
    cy.wait('@get-form');
    cy.get('#field-comment_message')
      .find('.CodeMirror textarea')
      .type(project.comment, { force: true });
    cy.wait(1000);
    cy.get('button').contains('Post comment').click();
    cy.wait('@post-comment');
    var cid = window.location.hash;
    cy.get('.comment__body').contains(project.comment);
    cy.get('.comment__header').contains(user.username);

    cy.wait(2000);
    cy.get('a[data-cy="comment-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy="edit"]').click();
    cy.wait('@edit-form');
    cy.get('#field-comment_message')
      .find('.CodeMirror textarea')
      .type(project.edit_comment, { force: true });
    cy.wait(1000);
    cy.get('button').contains('Edit comment').click();
    cy.wait('@edit-comment');
    cy.get(`${cid} .comment__body`).contains(project.edit_comment);

    cy.get('a[data-cy="reply"]').click();
    cy.wait('@reply-form');
    cy.get('#field-comment_message')
      .find('.CodeMirror textarea')
      .type(project.reply_comment, { force: true });
    cy.wait(1000);
    cy.get('button').contains('Post comment').click();
    cy.wait('@reply-comment');
    cid = window.location.hash;
    cy.get(`${cid} .comment__body`).contains(project.reply_comment);
    cy.wait(1000);
    cy.visit('/');

    /*

    The test for deleting comments has been disabled as it
    interferes with the comment notification test. To be added back later.

    cy.get('a[data-cy="comment-menu"]:visible').eq(1).click();
    cy.wait(1000);
    cy.get('a[data-cy="delete"]:visible').click();
    cy.wait('@delete-form');
    cy.get('button').contains('Delete').click();
    cy.wait('@delete-comment');
    cy.get('.comment__body')
      .contains(project.reply_comment)
      .should('not.exist');
    cy.wait(5000); */

    cy.logout();

    cy.login('/', hguser.username, hguser.password);
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="comments"]').click();
    cy.get('p.mui-panel').contains('You need to be a participant to comment.');

    cy.logout();
    cy.login('/', editor.username, editor.password);
    cy.visit('/updates');
    cy.wait('@fetch-updates');
    cy.contains('left comments');
  });
});
