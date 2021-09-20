/* eslint-disable global-require */
describe('Add a new submission', () => {
  const { user } = require('../fixtures/user.json');
  const { editor } = require('../fixtures/user.json');
  const profile = require('../fixtures/profile.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');

  it('Add submission', () => {
    cy.server();
    cy.route('GET', '**/admin').as('fetch-admin-panel');
    cy.route('GET', '**/updates?*').as('fetch-updates');
    cy.route('POST', '**/new').as('post-comment');

    cy.login('/', user.username, user.password);

    cy.get(`a[data-cy-title="${project.title}"]`).click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="submissions"]').click();
    cy.get('a[data-cy="propose-a-session"]:visible').click();
    cy.location('pathname').should('contain', 'new');
    cy.get('#title').type(proposal.title);
    cy.get('#field-body')
      .find('.CodeMirror textarea')
      .type(proposal.content, { force: true });
    cy.get('a[data-cy="add-video"]').click();
    cy.wait(1000);
    cy.get('#field-video_url').type(proposal.preview_video);
    cy.get('button[data-cy="save"]').click();
    cy.get('a[data-cy="add-label"]').click();
    cy.wait(1000);
    cy.get('fieldset').find('.listwidget').eq(0).find('input').eq(0).click();
    cy.get('fieldset').find('.listwidget').eq(1).find('input').eq(0).click();
    cy.get('button[data-cy="save"]').click();
    cy.get('button[data-cy="form-submit-btn"]').click();

    cy.get('[data-cy="proposal-title"]')
      .should('exist')
      .contains(proposal.title);
    cy.get('[data-cy="proposal-video"]').find('iframe').should('be.visible');
    cy.get('a[data-cy="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('[data-cy-admin="edit"]').should('exist');
    cy.get('[data-cy-admin="delete"]').should('exist');
    cy.get('[data-cy="edit-proposal-video"]').should('exist');

    cy.get('[data-cy="post-comment"]').click();
    cy.get('[data-cy="new-form"]')
      .find('.CodeMirror textarea')
      .type(proposal.proposer_note, { force: true });
    cy.wait(1000);
    cy.get('[data-cy="new-form"]').find('[data-cy="submit-comment"]').click();
    cy.wait('@post-comment');
    cy.get('.comment__body').contains(proposal.proposer_note);
    cy.get('.comment__header').contains(user.username);
  });
});
