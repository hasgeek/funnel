/* eslint-disable global-require */
describe('Add sponsor to project', () => {
  const { owner } = require('../fixtures/user.json');
  const project = require('../fixtures/project.json');
  const sponsor = require('../fixtures/sponsor.json');

  it('Add sponsor', () => {
    cy.server();
    cy.route('GET', '**/sponsors/add').as('add-sponsor-form');
    cy.route('POST', '**/sponsors/add').as('add-sponsor');
    cy.route('GET', '**/sponsors/**/edit').as('edit-sponsor-form');
    cy.route('POST', '**/sponsors/**/edit').as('edit-sponsor');
    cy.route('GET', '**/sponsors/**/remove').as('remove-sponsor-form');

    cy.login('/', owner.username, owner.password);
    cy.get('.upcoming')
      .find('.card--upcoming')
      .contains(project.title)
      .click({ force: true });
    cy.get('a[data-testid="site-editor-menu"]:visible').click();
    cy.get('a[data-testid="add-sponsor"]').click();
    cy.wait('@add-sponsor-form');
    cy.get('.select2-selection__arrow').click({ multiple: true });
    cy.get('.select2-search__field').type(sponsor.name, {
      force: true,
    });
    cy.get('.select2-results__option--highlighted', { timeout: 20000 }).should(
      'be.visible'
    );
    cy.get('.select2-results__option').contains(sponsor.name).click();
    cy.get('.select2-results__options', { timeout: 10000 }).should('not.exist');
    cy.get('button[data-testid="form-submit-btn"]').click();
    cy.wait(2000);
    cy.get('[data-testid="profile-link"]').contains(sponsor.title);

    cy.get('a[data-testid="edit-sponsor"]:visible').click();
    cy.wait('@edit-sponsor-form');
    cy.get('#is_promoted').click();
    cy.get('button[data-testid="form-submit-btn"]').click();
    cy.wait(2000);
    cy.get('[data-testid="sponsor-card"]').find('[data-testid="promoted"]').should('exist');

    cy.get('a[data-testid="remove-sponsor"]:visible').click();
    cy.wait('@remove-sponsor-form');
    cy.get('input[value="Remove"]').click();
    cy.get('[data-testid="sponsor-card"]').should('not.exist');
  });
});
