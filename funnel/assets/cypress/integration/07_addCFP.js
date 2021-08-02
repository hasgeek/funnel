/* eslint-disable global-require */
describe('Add CFP and labels to project', () => {
  const { editor } = require('../fixtures/user.json');
  const cfp = require('../fixtures/cfp.json');
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');
  const dayjs = require('dayjs');
  const labels = require('../fixtures/labels.json');

  it('Add CFP and labels', () => {
    var boxCoords = {};

    cy.login(
      `/${profile.title}/${project.url}`,
      editor.username,
      editor.password
    );

    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-navbar="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="add-cfp"]').click();
    cy.location('pathname').should('contain', '/cfp');
    cy.get('#field-instructions')
      .find('.CodeMirror textarea')
      .type(cfp.instructions, { force: true });
    cy.get('button[name="open-now"]').click();
    const cfpEndDay = dayjs().add(20, 'days').format('YYYY-MM-DDTHH:mm');
    cy.get('#cfp_end_at').type(cfpEndDay);
    cy.get('button[data-cy="add-cfp"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-navbar="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('button[data-cy-cfp=open_cfp]').click();
    cy.location('pathname').should('contain', project.url);

    cy.get('a[data-cy="project-menu"]:visible').click();
    cy.wait(1000);
    cy.get('a[data-cy-navbar="settings"]:visible').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('[data-cy="cfp-state"]').contains('Open');
    cy.get('a[data-cy="manage-labels"').click();
    cy.location('pathname').should('contain', '/labels');

    cy.fixture('labels').then((flabels) => {
      flabels.forEach((label) => {
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

    cy.get('.ui-draggable-box').then(($target) => {
      boxCoords = $target[1].getBoundingClientRect();
      cy.get('.ui-draggable-box')
        .eq(0)
        .find('.drag-handle')
        .trigger('mouseover', { which: 1, force: true, view: window })
        .trigger('mousedown', { which: 1, force: true, view: window })
        .trigger('mousemove', {
          pageX: boxCoords.left,
          pageY: boxCoords.bottom + boxCoords.height,
          view: window,
        })
        .trigger('mouseup', { force: true, view: window });
    });

    cy.get('button[data-cy="save-label-seq"]').click();

    cy.get('.ui-draggable-box')
      .eq(0)
      .find('.label-box__inner__heading')
      .contains(labels[1].title);
  });
});
