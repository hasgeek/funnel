# -*- coding: utf-8 -*-

from flask import render_template, redirect, flash, abort
from coaster.views import load_models, UrlForView, ModelView, route, render_with, requires_permission
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
        return redirect(project.url_for('sections'), code=303)
    return render_form(form=form, title=_("New section"), submit=_("Create section"))


@route('/<profile>/<project>/sections/<section>')
class SectionView(UrlForView, ModelView):
    model = Section
    route_model_map = {'profile': 'project.profile.name', 'project': 'project.name', 'section': 'name'}
    __decorators__ = [lastuser.requires_login]

    def loader(self, kwargs):
        return self.model.query.join(Project).join(Profile).filter(
                Project.name == kwargs.get('project'), Profile.name == kwargs.get('profile'),
                Section.name == kwargs.get('section')
            ).first_or_404()

    @route('', methods=['GET'])
    @render_with('section.html.jinja2', json=True)
    @requires_permission('view-section')
    def view(self, **kwargs):
        return {'project': self.obj.project.current_access(), 'section': self.obj.current_access()}

    @route('edit', methods=['GET', 'POST'])
    @requires_permission('edit-section')
    def edit(self, **kwargs):
        form = SectionForm(obj=self.obj, model=Section, parent=self.obj.parent)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your section has been edited"), 'info')
            return redirect(self.obj.project.url_for('sections'), code=303)
        return render_form(form=form, title=_("Edit section"), submit=_("Save changes"))

    @route('delete', methods=['GET', 'POST'])
    @requires_permission('delete-section')
    def delete(self, **kwargs):
        return render_delete_sqla(self.obj, db, title=_(u"Confirm delete"),
            message=_(u"Do you really wish to delete section '{title}’?").format(title=self.obj.title),
            success=_("Your section has been deleted"),
            next=self.obj.project.url_for('sections'),
            cancel_url=self.obj.project.url_for('sections'))


@route('/<project>/sections/<section>', subdomain='<profile>')
class FunnelSectionView(SectionView):
    pass


SectionView.init_app(app)
FunnelSectionView.init_app(funnelapp)
