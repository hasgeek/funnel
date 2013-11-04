# -*- coding: utf-8 -*-

from flask import render_template, redirect, request, flash
from coaster.views import load_models, load_model
from baseframe import _

from .. import app, lastuser
from ..models import db, ProposalSpace, ProposalSpaceSection
from ..forms import SectionForm, ConfirmDeleteForm


@app.route('/<space>/sections')
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('view-section', 'siteadmin'), addlperms=lastuser.permissions)
def section_list(space):
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space).all()
    return render_template('sections.html', space=space, sections=sections,
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('sections'), _("Sections"))])


@app.route('/<space>/sections/<section>')
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'),
    permission=('view-section', 'siteadmin'), addlperms=lastuser.permissions)
def section_view(space, section):
    return render_template('section.html', space=space, section=section,
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('sections'), _("Sections")),
            (section.url_for(), section.title)])


@app.route('/<space>/sections/new', methods=['GET', 'POST'])
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('new-section', 'siteadmin'), addlperms=lastuser.permissions)
def section_new(space):
    form = SectionForm(model=ProposalSpaceSection, parent=space)
    if form.validate_on_submit():
        section = ProposalSpaceSection(proposal_space=space)
        form.populate_obj(section)
        db.session.add(section)
        db.session.commit()
        flash(_("Your new section has been added"), 'info')
        return redirect(space.url_for(), code=303)
    return render_template('baseframe/autoform.html', form=form, title=_("New section"), submit=_("Create section"),
        breadcrumbs=[(space.url_for(), space.title), (space.url_for('sections'), _("Sections"))])


@app.route('/<space>/sections/<section>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'),
    permission=('edit-section', 'siteadmin'), addlperms=lastuser.permissions)
def section_edit(space, section):
    form = SectionForm(obj=section, model=ProposalSpaceSection, parent=space)
    if form.validate_on_submit():
        form.populate_obj(section)
        db.session.commit()
        flash(_("Your section has been edited"), 'info')
        return redirect(space.url_for(), code=303)
    return render_template('baseframe/autoform.html', form=form, title=_("Edit section"), submit=_("Save changes"),
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('sections'), _("Sections")),
            (section.url_for(), section.title)])


@app.route('/<space>/sections/<section>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'),
    permission=('delete-section', 'siteadmin'), addlperms=lastuser.permissions)
def section_delete(space, section):
    form = ConfirmDeleteForm()
    if form.validate_on_submit():
        if 'delete' in request.form:
            db.session.delete(section)
            db.session.commit()
            flash(_("Your section has been deleted"), 'info')
        return redirect(space.url_for(), code=303)
    return render_template('delete.html', form=form, title=_(u"Confirm delete"),
        message=_(u"Do you really wish to delete section ‘{title}’?").format(title=section.title),
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('sections'), _("Sections")),
            (section.url_for(), section.title)])
