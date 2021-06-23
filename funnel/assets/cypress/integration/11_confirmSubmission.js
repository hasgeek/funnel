describe('Confirm submission', function () {
  const editor = require('../fixtures/user.json').editor;
  const member = require('../fixtures/user.json').user;
  const profile = require('../fixtures/profile.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');
  const labels = require('../fixtures/labels.json');

  it('Confirm submission', function () {
    cy.server();
    cy.route('GET', '**/admin').as('fetch-admin-panel');
    cy.route('GET', '**/updates?*').as('fetch-updates');
    cy.route('POST', '**/new').as('post-comment');
    cy.route('GET', '**/comments').as('fetch-comment-sidebar');

    cy.login('/', editor.username, editor.password);

    cy.get('a[data-cy-title="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="submissions"]').click();
    cy.get('#search').type(proposal.title);
    cy.get('a[data-cy-proposal="' + proposal.title + '"]').click();

    cy.get('a[data-cy="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy="editor-panel"]:visible').click();
    cy.wait('@fetch-admin-panel');
    cy.get('#label-select').click();
    cy.get('#label-dropdown label').contains(labels[1].title).click();
    cy.get('#label-dropdown label').contains(labels[3].title).click();
    cy.get('#label-select').click();
    cy.get('form.add-label-form')
      .find('button[data-cy="form-submit-btn"]')
      .click();
    cy.fixture('labels').then((labels) => {
      labels.forEach(function (label) {
        if (label.label1) {
          cy.get('.label').contains(label.title + ': ' + label.label1);
        } else {
          cy.get('.label').contains(label.title);
        }
      });
    });

    cy.get('a[data-cy="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy="editor-panel"]:visible').click();
    cy.wait('@fetch-admin-panel');
    cy.get('[data-cy="proposal-status"]')
      .find('button[value="awaiting_details"]')
      .click();

    cy.get('a[data-cy="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy="editor-panel"]:visible').click();
    cy.wait('@fetch-admin-panel');
    cy.get('[data-cy="proposal-status"]')
      .find('button[value="under_evaluation"]')
      .click();

    cy.get('a[data-cy="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy="editor-panel"]:visible').click();
    cy.wait('@fetch-admin-panel');
    cy.get('[data-cy="proposal-status"]')
      .find('button[value="confirm"]')
      .click();
    cy.get('a[data-cy="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('input#featured-proposal-desktop').click({ force: true });

    cy.get('[data-cy="post-comment"]').click();
    cy.get('[data-cy="new-form"]')
      .find('.CodeMirror textarea')
      .type(proposal.comment, { force: true });
    cy.wait(1000);
    cy.get('[data-cy="new-form"]').find('[data-cy="submit-comment"]').click();
    cy.wait('@post-comment');
    var cid = window.location.hash;
    cy.get(`${cid} .comment__body`).contains(proposal.comment);
    cy.get(`${cid} .comment__header`).contains(editor.username);

    cy.get('a[data-cy="project-page"]').click();
    cy.get('[data-cy="proposal-card"]').contains(proposal.title).click();
    cy.get('a[data-cy="proposal-menu"]:visible').click();
    cy.wait(1000);
    cy.get('input#featured-proposal-desktop').click({ force: true });
    cy.get('a[data-cy="project-page"]').click();
    cy.get('[data-cy="proposal-card"]').should('not.exist');

    cy.visit('/');
    cy.logout();
    cy.wait(1000);

    cy.login('/' + profile.title, member.username, member.password);
    cy.visit('/updates');
    cy.wait('@fetch-updates');
    cy.get('[data-cy="notification-box"]').contains(proposal.title);
    cy.get('[data-cy="notification-box"]').contains(proposal.comment);
    cy.get('[data-cy="comment-sidebar"]').click();
    cy.wait('@fetch-comment-sidebar');
    cy.get('[data-cy="unread-comment"]').should('exist');
  });
});
