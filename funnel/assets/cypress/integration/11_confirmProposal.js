describe('Confirm proposal', function () {
  const editor = require('../fixtures/user.json').editor;
  const profile = require('../fixtures/profile.json');
  const proposal = require('../fixtures/proposal.json');
  const project = require('../fixtures/project.json');
  const labels = require('../fixtures/labels.json');

  it('Confirm proposal', function () {
    cy.server();
    cy.route('GET', '**/new').as('get-form');

    cy.login('/' + profile.title, editor.username, editor.password);

    cy.get('a[data-cy-title="' + project.title + '"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="proposals"]').click();
    cy.location('pathname').should('contain', 'proposals');
    cy.get('#search').type(proposal.title);
    cy.get('a[data-cy-proposal="' + proposal.title + '"]').click();

    cy.get('#label-select').click();
    cy.get('#label-dropdown label').contains(labels[2].title).click();
    cy.get('#label-dropdown label').contains(labels[3].title).click();
    cy.get('#label-select').click();
    cy.get('button[name="add-label"]').click();

    cy.fixture('labels').then((labels) => {
      labels.forEach(function (label) {
        if (label.label1) {
          cy.get('.label').contains(label.title + ': ' + label.label1);
        } else {
          cy.get('.label').contains(label.title);
        }
      });
    });
    cy.get('[data-cy="proposal-status"]')
      .find('button[value="awaiting_details"]')
      .click();
    cy.get('[data-cy="proposal-status"]')
      .find('button[value="under_evaluation"]')
      .click();
    cy.get('[data-cy="proposal-status"]')
      .find('button[value="confirm"]')
      .click();
    cy.get('[data-cy-proposal-status="Confirmed"]').should('exist');

    cy.get('[data-cy="post-comment"]').click();
    cy.wait('@get-form');
    cy.get('#field-comment_message')
      .find('.CodeMirror textarea')
      .type(proposal.comment, { force: true });
    cy.get('button').contains('Post comment').click();
    cy.wait(1000);
    var cid = window.location.hash;
    cy.get(`${cid} .comment--body`).contains(proposal.comment);
    cy.get(`${cid} .comment--header`).contains(editor.username);
  });
});
