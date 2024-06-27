import { admin, promoter, usher, editor, hguser } from '../fixtures/user.json';
import profile from '../fixtures/profile.json';
import project from '../fixtures/project.json';

describe('Adding crew', () => {
  Cypress.on('uncaught:exception', () => {
    return false;
  });

  it('Add crew to project', () => {
    cy.login(`/${profile.title}`, admin.username, admin.password);
    cy.get(`[data-cy-title="${project.title}"]`).first().click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="crew"]').click();
    cy.get('[data-cy="member"]')
      .contains(admin.username)
      .parents('.member')
      .find('[data-cy="role"]')
      .contains('Editor');

    cy.add_member(promoter.username, 'promoter');
    cy.add_member(usher.username, 'usher');
    cy.add_member(editor.username, 'editor');
    cy.add_member(hguser.username, 'usher', true);
  });
});
