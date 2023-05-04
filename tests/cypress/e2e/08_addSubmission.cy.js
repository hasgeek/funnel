/* eslint-disable global-require */
describe('Add a new submission', () => {
  const { user, editor, usher } = require('../fixtures/user.json');
  const profile = require('../fixtures/profile.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');

  it('Add submission', () => {
    cy.server();
    cy.route('GET', '**/admin').as('fetch-admin-panel');
    cy.route('GET', '**/updates?*').as('fetch-updates');
    cy.route('POST', '**/new').as('post-comment');
    cy.route('GET', '**/collaborator/*').as('get-collaborator-form');
    cy.route('POST', '**/collaborator/new').as('add-collaborator');

    cy.login('/', user.username, user.password);

    cy.get(`a[data-cy-title="${project.title}"]`).click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy="propose-a-session"]:visible').click();
    cy.location('pathname').should('contain', 'new');
    cy.get('#title').type(proposal.title);
    cy.get('#field-body')
      .find('.cm-editor .cm-line')
      .type(proposal.content, { force: true });
    cy.get('a[data-cy="add-video"]').click();
    cy.wait(1000);
    cy.get('#field-video_url').type(proposal.preview_video);
    cy.get('a[data-cy="save"]:visible').click();
    cy.get('a[data-cy="add-label"]').click();
    cy.wait(1000);
    cy.get('fieldset').find('.listwidget').eq(0).find('input').eq(0).click();
    cy.get('fieldset').find('.listwidget').eq(1).find('input').eq(0).click();
    cy.wait(2000);
    cy.get('a[data-cy="save"]:visible').click();
    cy.get('button[data-cy="form-submit-btn"]').click();

    cy.get('[data-cy="proposal-title"]').should('exist').contains(proposal.title);
    cy.get('[data-cy="proposal-video"]').find('iframe').should('be.visible');
    cy.get('a[data-cy="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('[data-cy-admin="edit"]:visible').click();

    cy.get('a[data-cy="add-collaborator-modal"]').click();
    cy.get('a[data-cy="add-collaborator"]').click();
    cy.wait('@get-collaborator-form');
    cy.get('.select2-search__field').type(usher.username, {
      force: true,
    });
    cy.get('.select2-results__option--highlighted', { timeout: 20000 }).should(
      'be.visible'
    );
    cy.get('.select2-results__option').contains(usher.username).click();
    cy.get('.select2-results__options', { timeout: 10000 }).should('not.exist');
    cy.get('#field-label').type('Editor');
    cy.get('.modal').find('button[data-cy="form-submit-btn"]:visible').click();
    cy.wait('@add-collaborator');
    cy.get('a.modal__close').click();
    cy.wait(6000); // Wait for toastr notice to fade out
    cy.get('button[data-cy="form-submit-btn"]').click();
    cy.get('.user__box__userid').contains(usher.username);
    cy.get('.badge').contains('Editor');

    cy.get('a[data-cy="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('[data-cy-admin="delete"]').should('exist');
    cy.get('[data-cy="edit-proposal-video"]').should('exist');

    cy.get('[data-cy="post-comment"]').click();
    cy.get('[data-cy="new-form"]')
      .find('.cm-editor .cm-line')
      .type(proposal.proposer_note, { force: true });
    cy.wait(1000);
    cy.get('[data-cy="new-form"]').find('[data-cy="submit-comment"]').click();
    cy.wait('@post-comment');
    cy.get('.comment__body').contains(proposal.proposer_note);
    cy.get('.comment__header').contains(user.username);
  });
});
