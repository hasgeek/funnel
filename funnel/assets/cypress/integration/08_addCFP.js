describe('Add CFP to project', function() {
  const editor = require('../fixtures/user.json').editor;
  const cfp = require('../fixtures/cfp.json');
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');

  it('Add CFP', function() {
    cy.login(
      '/' + profile.title + '/' + project.url,
      editor.username,
      editor.password
    );

    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="add-cfp"]').click();
    cy.location('pathname').should('contain', '/cfp');

    cy.get('#field-instructions')
      .find('.CodeMirror textarea')
      .type(cfp.instructions, { force: true });
    cy.get('button[name="open-now"]').click();
    var today = Cypress.moment().format('YYYY-MM-DD');
    var cfpEndDay = Cypress.moment(today)
      .add(60, 'days')
      .format('YYYY-MM-DD');
    var time = Cypress.moment().format('HH:mm');
    cy.get('#cfp_end_at-date').type(cfpEndDay);
    cy.get('#cfp_end_at-time').type(time);
    cy.get('button[data-cy="add-cfp"]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('button[data-cy-cfp=open_cfp]').click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('[data-cy="cfp-state"]').contains('Open');
  });
});
