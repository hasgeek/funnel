/* eslint-disable global-require */
describe('Confirm submission', () => {
  const { editor } = require('../fixtures/user.json');
  const member = require('../fixtures/user.json').user;
  const profile = require('../fixtures/profile.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');
  const labels = require('../fixtures/labels.json');

  it('Confirm submission', () => {
    cy.server();
    cy.route('GET', '**/admin').as('fetch-admin-panel');
    cy.route('GET', '**/updates?*').as('fetch-updates');
    cy.route('POST', '**/new').as('post-comment');

    cy.login('/', editor.username, editor.password);
    cy.get('a[data-testid="my-updates"]:visible').click();
    cy.visit('/updates');
    cy.wait('@fetch-updates');
    cy.get('[data-testid="notification-box"]').contains(proposal.title);
    cy.get('a[data-testid="home-desktop"]').click();
    cy.get(`a[data-testid="${project.title}"]`).click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-testid="submissions"]').click();
    cy.get('#search').type(proposal.title);
    cy.get(`a[data-testid="${proposal.title}"]`).click();

    cy.get('a[data-testid="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="editor-panel"]:visible').click();
    cy.wait('@fetch-admin-panel');
    cy.get('#label-select').click();
    cy.get('#label-dropdown label').contains(labels[1].title).click();
    cy.get('#label-dropdown label').contains(labels[3].title).click();
    cy.get('#label-select').click();
    cy.get('form.add-label-form').find('button[data-testid="form-submit-btn"]').click();
    cy.fixture('labels').then((flabels) => {
      flabels.forEach((label) => {
        if (label.label1) {
          cy.get('.label').contains(`${label.title}: ${label.label1}`);
        } else {
          cy.get('.label').contains(label.title);
        }
      });
    });

    cy.get('a[data-testid="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="editor-panel"]:visible').click();
    cy.wait('@fetch-admin-panel');
    cy.get('[data-testid="proposal-status"]')
      .find('button[value="awaiting_details"]')
      .click();

    cy.get('a[data-testid="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="editor-panel"]:visible').click();
    cy.wait('@fetch-admin-panel');
    cy.get('[data-testid="proposal-status"]')
      .find('button[value="under_evaluation"]')
      .click();

    cy.get('a[data-testid="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-testid="editor-panel"]:visible').click();
    cy.wait('@fetch-admin-panel');
    cy.get('[data-testid="proposal-status"]').find('button[value="confirm"]').click();
    cy.get('a[data-testid="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('input#featured-proposal').click({ force: true });

    cy.get('[data-testid="post-comment"]').click();
    cy.get('[data-testid="new-form"]')
      .find('.cm-editor .cm-line')
      .type(proposal.comment, { force: true });
    cy.wait(1000);
    cy.get('[data-testid="new-form"]').find('[data-testid="submit-comment"]').click();
    cy.wait('@post-comment');
    const cid = window.location.hash;
    cy.get(`${cid} .comment__body`).contains(proposal.comment);
    cy.get(`${cid} .comment__header`).contains(editor.username);

    cy.get('a[data-testid="project-page"]').click();
    cy.get('[data-testid="proposal-card"]').contains(proposal.title).click();
    cy.get('a[data-testid="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('input#featured-proposal').click({ force: true });
    cy.get('a[data-testid="project-page"]').click();
    cy.get('[data-testid="proposal-card"]').should('not.exist');

    cy.visit('/');
    cy.logout();
    cy.wait(1000);

    cy.login(`/${profile.title}`, member.username, member.password);
    cy.visit('/updates');
    cy.wait('@fetch-updates');
    cy.get('[data-testid="notification-box"]').contains(proposal.title);
    cy.get('[data-testid="notification-box"]').contains(proposal.comment);
    cy.get('[data-testid="comment-sidebar"]').click();
    cy.wait(1000);
    cy.get('[data-testid="unread-comment"]').should('exist');
  });
});
