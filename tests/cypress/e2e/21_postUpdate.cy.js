import { user, editor, newuser } from '../fixtures/user.json';
import project from '../fixtures/project.json';

describe('Test updates feature', () => {
  it('Post update on project page', () => {
    cy.intercept('GET', '**/updates?*').as('fetch-updates');

    cy.login('/', editor.username, editor.password);
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="updates"]').click();

    cy.get('a[data-cy-btn="add-update"]').click();
    cy.get('#title').type(project.update_title);
    cy.get('#field-body')
      .find('.cm-editor .cm-line')
      .type(project.update_body, { force: true });
    cy.get('#is_pinned').click();
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.location('pathname').should('contain', 'updates');

    cy.get('a[data-cy-btn="add-update"]').click();
    cy.get('#title').type(project.restricted_update_title);
    cy.get('#field-body')
      .find('.cm-editor .cm-line')
      .type(project.restricted_update_body, { force: true });
    cy.get('#is_restricted').click();
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.logout();

    cy.login('/', user.username, user.password);
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('.pinned__update')
      .find('.pinned__update__heading')
      .contains(project.update_title);
    cy.get('a[data-cy-navbar="updates"]').click();
    cy.get('.update').contains(project.restricted_update_title);
    cy.get('a[data-cy="my-updates"]:visible').click();
    cy.wait('@fetch-updates');
    cy.get('[data-cy="notification-box"]').contains(project.update_title);
    cy.logout();

    cy.login('/', newuser.username, newuser.password);
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('.pinned__update')
      .find('.pinned__update__heading')
      .contains(project.update_title);
    cy.get('a[data-cy-navbar="updates"]').click();
    cy.get('.update__content')
      .contains(project.restricted_update_body)
      .should('not.exist');
    cy.logout();
  });
});
