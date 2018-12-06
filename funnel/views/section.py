# -*- coding: utf-8 -*-

from flask import flash, redirect, render_template
from coaster.views import ModelView, UrlForView, load_models, render_with, requires_permission, route
from baseframe import _
from baseframe.forms import render_delete_sqla, render_form

from .. import app, funnelapp, lastuser
from ..models import Profile, Project, ProjectRedirect, Section, db
from ..forms import SectionForm


def section_data(section):
    return {
        'name': section.name,
        'title': section.title,
        'description': section.description,
        'url': None,
        'json_url': None
        }


@route('/<profile>/<project>/sections')
class ProjectSectionView(UrlForView, ModelView):
    model = Project
    route_model_map = {'profile': 'profile.name', 'project': 'name'}

    def loader(self, profile, project):
        return self.model.query.join(Profile).filter(
                Project.name == project, Profile.name == profile
            ).first_or_404()

    @route('')
    @render_with('sections.html.jinja2')
    @lastuser.requires_login
    @requires_permission('view-section')
    def sections(self):
        return dict(project=self.obj, sections=self.obj.sections)


@route('/<project>/sections', subdomain='<profile>')
class FunnelProjectSectionView(ProjectSectionView):
    pass


ProjectSectionView.init_app(app)
FunnelProjectSectionView.init_app(funnelapp)


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

    def loader(self, profile, project, section):
        return self.model.query.join(Project).join(Profile).filter(
            Project.name == project, Profile.name == profile,
            Section.name == section
            ).first_or_404()

    @route('', methods=['GET'])
    @render_with('section.html.jinja2', json=True)
    @requires_permission('view-section')
    def view(self):
        return {'project': self.obj.project.current_access(), 'section': self.obj.current_access()}

    @route('edit', methods=['GET', 'POST'])
    @requires_permission('edit-section')
    def edit(self):
        form = SectionForm(obj=self.obj, model=Section, parent=self.obj.parent)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your section has been edited"), 'info')
            return redirect(self.obj.project.url_for('sections'), code=303)
        return render_form(form=form, title=_("Edit section"), submit=_("Save changes"))

    @route('delete', methods=['GET', 'POST'])
    @requires_permission('delete-section')
    def delete(self):
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
