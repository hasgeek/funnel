# -*- coding: utf-8 -*-

from flask import render_template, redirect, flash
from coaster.views import load_models
from baseframe import _
from baseframe.forms import render_form, render_delete_sqla

from .. import app, lastuser
from ..models import db, Profile, ProposalSpace, ProposalSpaceRedirect, ProposalSpaceSection
from ..forms import SectionForm


def section_data(section):
    return {
        'name': section.name,
        'title': section.title,
        'description': section.description,
        'url': None,
        'json_url': None
        }


@app.route('/<space>/sections', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view-section')
def section_list(profile, space):
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space).all()
    return render_template('sections.html', space=space, sections=sections)


@app.route('/<space>/sections/<section>', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'),
    permission='view-section')
def section_view(profile, space, section):
    return render_template('section.html', space=space, section=section)


@app.route('/<space>/sections/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-section')
def section_new(profile, space):
    form = SectionForm(model=ProposalSpaceSection, parent=space)
    if form.validate_on_submit():
        section = ProposalSpaceSection(proposal_space=space)
        form.populate_obj(section)
        db.session.add(section)
        db.session.commit()
        flash(_("Your new section has been added"), 'info')
        return redirect(space.url_for(), code=303)
    return render_form(form=form, title=_("New section"), submit=_("Create section"))


@app.route('/<space>/sections/<section>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'),
    permission='edit-section')
def section_edit(profile, space, section):
    form = SectionForm(obj=section, model=ProposalSpaceSection, parent=space)
    if form.validate_on_submit():
        form.populate_obj(section)
        db.session.commit()
        flash(_("Your section has been edited"), 'info')
        return redirect(space.url_for(), code=303)
    return render_form(form=form, title=_("Edit section"), submit=_("Save changes"))


@app.route('/<space>/sections/<section>/delete', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'),
    permission='delete-section')
def section_delete(profile, space, section):
    return render_delete_sqla(section, db, title=_(u"Confirm delete"),
        message=_(u"Do you really wish to delete section ‘{title}’?").format(title=section.title),
        success=_("Your section has been deleted"),
        next=space.url_for('sections'),
        cancel_url=space.url_for('sections'))
