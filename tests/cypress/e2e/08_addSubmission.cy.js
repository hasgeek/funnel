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

    cy.get(`a[data-testid="${project.title}"]`).click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-testid="propose-a-session"]:visible').click();
    cy.location('pathname').should('contain', 'new');
    cy.get('a[data-testid="close-consent-modal"]').click();
    cy.get('#title').type(proposal.title);
    cy.get('#field-body')
      .find('.cm-editor .cm-line')
      .type(proposal.content, { force: true });
    cy.get('a[data-testid="add-video"]').click();
    cy.wait(1000);
    cy.get('#field-video_url').type(proposal.preview_video);
    cy.get('a[data-testid="save"]:visible').click();
    cy.get('a[data-testid="add-label"]').click();
    cy.wait(2000);
    cy.get('fieldset').find('.listwidget').eq(0).find('input').eq(0).click();
    cy.wait(2000);
    cy.get('fieldset').find('.listwidget').eq(1).find('input').eq(0).click();
    cy.wait(2000);
    cy.get('a[data-testid="save"]:visible').click();
    cy.get('button[data-testid="form-submit-btn"]').click();

    cy.get('[data-testid="proposal-title"]').should('exist').contains(proposal.title);
    cy.get('[data-testid="proposal-video"]').find('iframe').should('be.visible');
    cy.get('a[data-testid="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('[data-testid="edit"]:visible').click();
    cy.get('a[data-testid="close-consent-modal"]').click();

    cy.get('a[data-testid="add-collaborator-modal"]').click();
    cy.get('a[data-testid="add-collaborator"]').click();
    cy.wait('@get-collaborator-form');
    cy.get('.select2-selection__arrow').click({ multiple: true });
    cy.get('.select2-search__field').type(usher.username, {
      force: true,
    });
    cy.get('.select2-results__option--highlighted', { timeout: 20000 }).should(
      'be.visible'
    );
    cy.get('.select2-results__option').contains(usher.username).click();
    cy.get('.select2-results__options', { timeout: 10000 }).should('not.exist');
    cy.wait(1000);
    cy.get('#field-label').click().type('Editor');
    cy.get('.modal').find('button[data-testid="form-submit-btn"]:visible').click();
    cy.wait('@add-collaborator');
    cy.get('a.modal__close:visible').click();
    cy.wait(6000); // Wait for toastr notice to fade out
    cy.get('button[data-testid="form-submit-btn"]').click();
    cy.get('.user__box__userid').contains(usher.username);
    cy.get('.badge').contains('Editor');

    cy.get('a[data-testid="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('[data-testid="delete"]').should('exist');
    cy.get('[data-testid="edit-proposal-video"]').should('exist');

    cy.get('[data-testid="post-comment"]').click();
    cy.get('[data-testid="new-form"]')
      .find('.cm-editor .cm-line')
      .type(proposal.proposer_note, { force: true });
    cy.wait(1000);
    cy.get('[data-testid="new-form"]').find('[data-testid="submit-comment"]').click();
    cy.wait('@post-comment');
    cy.get('.comment__body').contains(proposal.proposer_note);
    cy.get('.comment__header').contains(user.username);
  });
});
