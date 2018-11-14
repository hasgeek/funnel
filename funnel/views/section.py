# -*- coding: utf-8 -*-

from flask import render_template, redirect, flash
from coaster.views import load_models
from baseframe import _
from baseframe.forms import render_form, render_delete_sqla

from .. import app, funnelapp, lastuser
from ..models import db, Profile, Project, ProjectRedirect, Section
from ..forms import SectionForm


def section_data(section):
    return {
        'name': section.name,
        'title': section.title,
        'description': section.description,
        'url': None,
        'json_url': None
        }


@app.route('/<profile>/<project>/sections')
@funnelapp.route('/<project>/sections', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='view-section')
def section_list(profile, project):
    sections = Section.query.filter_by(project=project).all()
    return render_template('sections.html.jinja2', project=project, sections=sections)


@app.route('/<profile>/<project>/sections/<section>')
@funnelapp.route('/<project>/sections/<section>', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Section, {'name': 'section', 'project': 'project'}, 'section'),
    permission='view-section')
def section_view(profile, project, section):
    return render_template('section.html.jinja2', project=project, section=section)


@app.route('/<profile>/<project>/sections/new', methods=['GET', 'POST'])
@funnelapp.route('/<project>/sections/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='new-section')
def section_new(profile, project):
    form = SectionForm(model=Section, parent=project)
    if form.validate_on_submit():
        section = Section(project=project)
        form.populate_obj(section)
        db.session.add(section)
        db.session.commit()
        flash(_("Your new section has been added"), 'info')
        return redirect(project.url_for(), code=303)
    return render_form(form=form, title=_("New section"), submit=_("Create section"))


@app.route('/<profile>/<project>/sections/<section>/edit', methods=['GET', 'POST'])
@funnelapp.route('/<project>/sections/<section>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Section, {'name': 'section', 'project': 'project'}, 'section'),
    permission='edit-section')
def section_edit(profile, project, section):
    form = SectionForm(obj=section, model=Section, parent=project)
    if form.validate_on_submit():
        form.populate_obj(section)
        db.session.commit()
        flash(_("Your section has been edited"), 'info')
        return redirect(project.url_for(), code=303)
    return render_form(form=form, title=_("Edit section"), submit=_("Save changes"))


@app.route('/<profile>/<project>/sections/<section>/delete', methods=['GET', 'POST'])
@funnelapp.route('/<project>/sections/<section>/delete', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Section, {'name': 'section', 'project': 'project'}, 'section'),
    permission='delete-section')
def section_delete(profile, project, section):
    return render_delete_sqla(section, db, title=_(u"Confirm delete"),
        message=_(u"Do you really wish to delete section ‘{title}’?").format(title=section.title),
        success=_("Your section has been deleted"),
        next=project.url_for('sections'),
        cancel_url=project.url_for('sections'))
