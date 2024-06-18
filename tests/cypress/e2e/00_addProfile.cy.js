import { owner } from '../fixtures/user.json';
import sponsor from '../fixtures/sponsor.json';
describe('Profile', () => {
  it('Create a new profile', () => {
    cy.login('/', owner.username, owner.password);
    cy.get('#hgnav').find('a[data-cy="my-account"]').click();
    cy.wait(1000);
    cy.get('a[data-cy="org"]:visible').click();
    cy.get('a[data-cy="new"]').click();
    cy.get('#title').type(sponsor.title);
    cy.get('#name').type(sponsor.name);
    cy.get('button[data-cy="form-submit-btn"]').click();

    cy.logout();
  });
});
