describe('Test updates feature', function () {
  const editor = require('../fixtures/user.json').editor;
  const user = require('../fixtures/user.json').user;
  const newuser = require('../fixtures/user.json').newuser;
  const project = require('../fixtures/project.json');

  it('Post update on project page', function () {
    cy.login('/', editor.username, editor.password);
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="updates"]').click();

    cy.get('a[data-cy-btn="add-post"]').click();
    cy.get('#title').type(project.post_title);
    cy.get('#field-body')
      .find('.CodeMirror textarea')
      .type(project.post_body, { force: true });
    cy.get('#is_pinned').click();
    cy.get('button').contains('Save').click();
    cy.get('button').contains('Publish').click();
    cy.location('pathname').should('contain', 'updates');

    cy.get('a[data-cy-btn="add-post"]').click();
    cy.get('#title').type(project.restricted_post_title);
    cy.get('#field-body')
      .find('.CodeMirror textarea')
      .type(project.restricted_post_body, { force: true });
    cy.get('#restricted').click();
    cy.get('button').contains('Save').click();
    cy.get('button').contains('Publish').click();
    cy.logout();

    cy.login('/', user.username, user.password);
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('.pinned__post')
      .find('.pinned__post__body')
      .contains(project.post_title);
    cy.get('a[data-cy-navbar="updates"]').click();
    cy.get('.post').contains(project.restricted_post_title);
    cy.logout();

    cy.login('/', newuser.username, newuser.newpassword);
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('.pinned__post')
      .find('.pinned__post__body')
      .contains(project.post_title);
    cy.get('a[data-cy-navbar="updates"]').click();
    cy.get('.post__content')
      .contains(project.restricted_post_body)
      .should('not.exist');
    cy.logout();
  });
});
