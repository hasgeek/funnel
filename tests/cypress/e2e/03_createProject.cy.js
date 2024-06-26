import { admin } from '../fixtures/user.json';
import profile from '../fixtures/profile.json';
import project from '../fixtures/project.json';

describe('Project', () => {
  it('Create a new project', () => {
    cy.login(`/${profile.title}`, admin.username, admin.password);

    cy.get('a[data-cy="new-project"]').click();
    cy.location('pathname').should('contain', '/new');

    cy.get('#title').type(project.title);
    cy.get('#location').type(project.location);
    cy.get('#tagline').type(project.tagline);
    cy.get('#field-description')
      .find('.cm-editor .cm-line')
      .type(project.description, { force: true });
    cy.get('button[data-cy="form-submit-btn"]').click();

    cy.location('pathname').should('contain', project.url);
    cy.title().should('include', project.title);
    // TODO: After imgee merger, add tests to upload and select image
    cy.get('[data-cy="add-project-banner"]').should('exist');

    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-admin="edit"]:visible').click();
    cy.get('#tagline').type(project.tagline);
    cy.wait(3000);
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.title().should('include', project.title);
  });
});
