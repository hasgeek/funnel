import { owner } from '../fixtures/user.json';
import project from '../fixtures/project.json';
import sponsor from '../fixtures/sponsor.json';

describe('Add sponsor to project', () => {
  it('Add sponsor', () => {
    cy.intercept('GET', '**/sponsors/add').as('add-sponsor-form');
    cy.intercept('POST', '**/sponsors/add').as('add-sponsor');
    cy.intercept('GET', '**/sponsors/**/edit').as('edit-sponsor-form');
    cy.intercept('POST', '**/sponsors/**/edit').as('edit-sponsor');
    cy.intercept('GET', '**/sponsors/**/remove').as('remove-sponsor-form');

    cy.login('/', owner.username, owner.password);
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('a[data-cy="site-editor-menu"]:visible').click();
    cy.get('a[data-cy="add-sponsor"]').click();
    cy.wait('@add-sponsor-form');
    cy.get('.select2-selection__arrow').click({ multiple: true });
    cy.get('.select2-search__field').type(sponsor.name, {
      force: true,
    });
    cy.get('.select2-results__option--highlighted', { timeout: 20000 }).should(
      'be.visible',
    );
    cy.get('.select2-results__option').contains(sponsor.name).click();
    cy.get('.select2-results__options', { timeout: 10000 }).should('not.exist');
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.wait(2000);
    cy.get('[data-cy="profile-link"]').contains(sponsor.title);

    cy.get('a[data-cy="edit-sponsor"]:visible').click();
    cy.wait('@edit-sponsor-form');
    cy.get('#is_promoted').click();
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.wait(2000);
    cy.get('[data-cy="sponsor-card"]').find('[data-cy="promoted"]').should('exist');

    cy.get('a[data-cy="remove-sponsor"]:visible').click();
    cy.wait('@remove-sponsor-form');
    cy.get('input[value="Remove"]').click();
    cy.get('[data-cy="sponsor-card"]').should('not.exist');
  });
});
