# -*- coding: utf-8 -*-

from flask import flash, redirect, g, render_template
from coaster.views import render_with, requires_permission, route, UrlForView, ModelView
from baseframe import _
from baseframe.forms import render_delete_sqla, render_form

from .. import app, funnelapp, lastuser
from ..models import Label, db, Project, Profile
from ..forms import LabelForm
from .mixins import ProjectViewMixin
from .decorators import legacy_redirect


@route('/<profile>/<project>/labels')
class ProjectLabelView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('labels.html.jinja2')
    @lastuser.requires_login
    @requires_permission('edit_project')
    def labels(self):
        return dict(project=self.obj, labels=self.obj.labels)

    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('admin')
    def new_label(self):
        form = LabelForm(obj=self.obj, model=Label, parent=self.obj.parent)
        # return jsonify(
            # title="Add label",
            # form=render_template('labels_form.html.jinja2', title="Add label", form=form, project=self.obj))
        return render_template('labels_form.html.jinja2', title="Add label", form=form, project=self.obj)


@route('/<project>/labels', subdomain='<profile>')
class FunnelProjectLabelView(ProjectLabelView):
    pass


ProjectLabelView.init_app(app)
FunnelProjectLabelView.init_app(funnelapp)


@route('/<profile>/<project>/labels/<label>')
class LabelView(UrlForView, ModelView):
    __decorators__ = [lastuser.requires_login, legacy_redirect]
    model = Label
    route_model_map = {
        'profile': 'project.profile.name', 'project': 'project.name',
        'label': 'name'}

    def loader(self, profile, project, label):
        proj = Project.query.join(Profile).filter(
                Profile.name == profile, Project.name == project
            ).first_or_404()
        label = self.model.query.filter_by(project=proj, name=label).first_or_404()
        g.profile = label.project.profile
        return label

    @route('edit', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
    def edit(self):
        form = LabelForm(obj=self.obj, model=Label, parent=self.obj.parent)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your label has been edited"), 'info')
            return redirect(self.obj.project.url_for('labels'), code=303)
        return render_form(form=form, title=_("Edit label"), submit=_("Save changes"))


@route('/<project>/labels/<label>', subdomain='<profile>')
class FunnelLabelView(LabelView):
    pass


LabelView.init_app(app)
FunnelLabelView.init_app(funnelapp)
