describe('Test comments feature', function () {
  const user = require('../fixtures/user.json').user;
  const hguser = require('../fixtures/user.json').hguser;
  const project = require('../fixtures/project.json');

  it('Post comment on project page', function () {
    cy.server();
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

    cy.get('#field-comment_message')
      .find('.CodeMirror textarea')
      .type(project.comment, { force: true });
    cy.get('#comment-form').submit();
    cy.wait(1000);
    var cid = window.location.hash;
    cy.get('.comment--body').contains(project.comment);
    cy.get('.comment--header').contains(user.username);

    cy.get('a[data-cy="edit"]').click();
    cy.wait('@edit-comment');
    cy.get('#field-comment_message')
      .find('.CodeMirror textarea')
      .type(project.edit_comment, { force: true });
    cy.get('#comment-form').submit();
    cy.wait(1000);
    cy.get(`${cid} .comment--body`).contains(project.edit_comment);

    cy.get('a[data-cy="reply"]').click();
    cy.get('#field-comment_message')
      .find('.CodeMirror textarea')
      .type(project.reply_comment, { force: true });
    cy.get('#comment-form').submit();
    cy.wait(1000);
    cid = window.location.hash;
    cy.get(`${cid} .comment--body`).contains(project.reply_comment);

    cy.get('a[data-cy="delete"]').first().click();
    cy.get('[data-cy="delete-comment"]').click();
    cy.get('.comment--body').contains(project.comment).should('not.exist');
    cy.logout();

    cy.login('/', hguser.username, hguser.password);
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="comments"]').click();
    cy.get('p.mui-panel').contains('You need to be a participant to comment.');
  });
});
