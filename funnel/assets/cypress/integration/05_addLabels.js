describe('Project', function() {
  const admin = require('../fixtures/admin.json');
  const project = require('../fixtures/project.json');

  it('Add labels', function() {
    cy.login('/JSFoo/' + project.url, admin.username, admin.password);

    cy.get('a[data-cy="labels"').click();
    cy.location('pathname').should('contain', '/labels');

    cy.fixture('labels').then(labels => {
      labels.forEach(function(label) {
        cy.get('a[data-cy="add-labels"]').click();
        cy.location('pathname').should('contain', '/new');

        cy.get('#title').type(label.title);
        cy.get('.emojionearea-button').click();
        cy.get('.emojionearea-picker').should('be.visible');
        cy.get(
          '.emojionearea-category[name="smileys_people"] i[title="Grinning"]'
        ).click();
        cy.get('.emojionearea-picker').should('be.hidden');

        cy.get('#add-sublabel-form').click();
        cy.get('#child-form > .ui-dragable-box')
          .eq(0)
          .should('be.visible');
        cy.get('#child-form > .ui-dragable-box')
          .eq(0)
          .find('#title')
          .type(label.label1);
        cy.get('#child-form > .ui-dragable-box')
          .eq(0)
          .find('.emojionearea-button')
          .click();
        cy.get('#child-form > .ui-dragable-box')
          .eq(0)
          .find('.emojionearea-picker')
          .should('be.visible');
        cy.get('#child-form > .ui-dragable-box')
          .eq(0)
          .find(
            '.emojionearea-category[name="smileys_people"] i[title="Relaxed"]'
          )
          .click();
        cy.get('#child-form > .ui-dragable-box')
          .eq(0)
          .find('.emojionearea-picker')
          .should('be.hidden');

        cy.get('#add-sublabel-form').click();
        cy.get('#child-form > .ui-dragable-box')
          .eq(1)
          .should('be.visible');
        cy.get('#child-form > .ui-dragable-box')
          .eq(1)
          .find('#title')
          .type(label.label2);
        cy.get('#child-form > .ui-dragable-box')
          .eq(1)
          .find('.emojionearea-button')
          .click();
        cy.get('#child-form > .ui-dragable-box')
          .eq(1)
          .find('.emojionearea-picker')
          .should('be.visible');
        cy.get('#child-form > .ui-dragable-box')
          .eq(1)
          .find(
            '.emojionearea-category[name="smileys_people"] i[title="Smile"]'
          )
          .click();
        cy.get('#child-form > .ui-dragable-box')
          .eq(1)
          .find('.emojionearea-picker')
          .should('be.hidden');

        if (label.adminLabel) {
          cy.get('#field-restricted')
            .find('label')
            .click();
        }
        cy.get('button[data-cy-submit="save-label"]').click();
        cy.location('pathname').should('contain', '/labels');
      });
    });
  });
});
