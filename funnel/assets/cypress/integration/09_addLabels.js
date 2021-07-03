describe('Add labels to project', function () {
  const editor = require('../fixtures/user.json').editor;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');
  const labels = require('../fixtures/labels.json');

  it('Add labels', function () {
    cy.login(
      '/' + profile.title + '/' + project.url,
      editor.username,
      editor.password
    );

    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-navbar="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="manage-labels"').click();
    cy.location('pathname').should('contain', '/labels');

    cy.fixture('labels').then((labels) => {
      labels.forEach(function (label) {
        cy.get('a[data-cy="add-labels"]').click();
        cy.location('pathname').should('contain', '/new');

        cy.get('#title').type(label.title);
        cy.get('.emojionearea-button').click();
        cy.get('.emojionearea-picker').should('be.visible');
        cy.get(
          '.emojionearea-category[name="smileys_people"] i[title="Innocent"]'
        ).click();
        cy.get('.emojionearea-picker').should('be.hidden');

        if (label.label1) {
          cy.get('#add-sublabel-form').click();
          cy.get('#child-form > .ui-draggable-box').eq(0).should('be.visible');
          cy.get('#child-form > .ui-draggable-box')
            .eq(0)
            .find('#title')
            .type(label.label1);
          cy.get('#child-form > .ui-draggable-box')
            .eq(0)
            .find('.emojionearea-button')
            .click();
          cy.get('#child-form > .ui-draggable-box')
            .eq(0)
            .find('.emojionearea-picker')
            .should('be.visible');
          // Emoji Relaxed is throwing not a valid emoji error
          cy.get('#child-form > .ui-draggable-box')
            .eq(0)
            .find(
              '.emojionearea-category[name="smileys_people"] i[title="Joy"]'
            )
            .click();
          cy.get('#child-form > .ui-draggable-box')
            .eq(0)
            .find('.emojionearea-picker')
            .should('be.hidden');
        }

        if (label.label2) {
          cy.get('#add-sublabel-form').click();
          cy.get('#child-form > .ui-draggable-box').eq(1).should('be.visible');
          cy.get('#child-form > .ui-draggable-box')
            .eq(1)
            .find('#title')
            .type(label.label2);
          cy.get('#child-form > .ui-draggable-box')
            .eq(1)
            .find('.emojionearea-button')
            .click();
          cy.get('#child-form > .ui-draggable-box')
            .eq(1)
            .find('.emojionearea-picker')
            .should('be.visible');
          cy.get('#child-form > .ui-draggable-box')
            .eq(1)
            .find(
              '.emojionearea-category[name="smileys_people"] i[title="Smile"]'
            )
            .click();
          cy.get('#child-form > .ui-draggable-box')
            .eq(1)
            .find('.emojionearea-picker')
            .should('be.hidden');
        }

        if (label.adminLabel) {
          cy.get('#field-restricted').find('label').click();
        }
        cy.get('button[data-cy-submit="save-label"]').click();
        cy.location('pathname').should('contain', '/labels');
      });
    });

    cy.get('.ui-draggable-box')
      .eq(0)
      .find('.drag-handle')
      .trigger('mouseover', { which: 1, force: true, view: window })
      .trigger('mousedown', { which: 1, force: true, view: window })
      .trigger('mousemove', {
        pageX: 500,
        pageY: 550,
        force: true,
        view: window,
      })
      .trigger('mouseup', { force: true, view: window });

    cy.get('button[data-cy="save-label-seq"]').click();

    cy.get('.ui-draggable-box')
      .eq(0)
      .find('.label-box__inner__heading')
      .contains(labels[1].title);
  });
});
