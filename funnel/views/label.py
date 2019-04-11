# -*- coding: utf-8 -*-

from flask import flash, redirect, g
from coaster.views import render_with, requires_permission, route, UrlForView, ModelView
from baseframe import _
from baseframe.forms import render_delete_sqla, render_form

from .. import app, funnelapp, lastuser
from ..models import Labelset, Label, db, Project, Profile
from ..forms import LabelsetForm, LabelForm
from .mixins import ProjectViewMixin
from .decorators import legacy_redirect


@route('/<profile>/<project>/labelsets')
class ProjectLabelsetView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('labels.html.jinja2')
    @lastuser.requires_login
    @requires_permission('edit_project')
    def labelsets(self):
        return dict(project=self.obj, labelsets=self.obj.labelsets)

    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new_labelset')
    def new_labelset(self):
        form = LabelsetForm(model=Labelset, parent=self.obj)
        if form.validate_on_submit():
            labelset = Labelset(project=self.obj)
            form.populate_obj(labelset)
            if 'assign_labelset' in self.obj.current_access():
                self.obj.current_access().assign_labelset(labelset)
                db.session.commit()
                flash(_("The labelset has been successfully created. Assign some labels to it."), 'info')
                return redirect(self.obj.url_for('labelsets'), code=303)
            else:
                flash(_("You don't have permission to create a new labelset for this project"), 'danger')
                return redirect(self.obj.url_for('labelsets'), code=303)
        return render_form(form=form, title=_("New labelset"), submit=_("Create labelset"))


@route('/<project>/labelsets', subdomain='<profile>')
class FunnelProjectLabelsetView(ProjectLabelsetView):
    pass


ProjectLabelsetView.init_app(app)
FunnelProjectLabelsetView.init_app(funnelapp)


@route('/<profile>/<project>/labelsets/<labelset>')
class LabelsetView(UrlForView, ModelView):
    __decorators__ = [legacy_redirect]
    model = Labelset
    route_model_map = {'profile': 'project.profile.name', 'project': 'project.name', 'labelset': 'name'}

    def loader(self, profile, project, labelset):
        labelset = self.model.query.join(Project).join(Profile).filter(
            Project.name == project, Profile.name == profile,
            Labelset.name == labelset
            ).first_or_404()
        g.profile = labelset.project.profile
        return labelset

    @route('edit', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
    def edit(self):
        form = LabelsetForm(obj=self.obj, model=Labelset, parent=self.obj.parent)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your labelset has been edited"), 'info')
            return redirect(self.obj.project.url_for('labelsets'), code=303)
        return render_form(form=form, title=_("Edit labelset"), submit=_("Save changes"))

    @route('delete', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
    def delete(self):
        return render_delete_sqla(self.obj, db, title=_(u"Confirm delete"),
            message=_(u"Do you really wish to delete labelset '{title}’?").format(title=self.obj.title),
            success=_("Your labelset has been deleted"),
            next=self.obj.project.url_for('labelsets'),
            cancel_url=self.obj.project.url_for('labelsets'))

    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new_labelset')
    def new_label(self):
        form = LabelForm(model=Label, parent=self.obj)
        if form.validate_on_submit():
            label = Label(labelset=self.obj)
            form.populate_obj(label)
            if 'assign_label' in self.obj.current_access():
                self.obj.current_access().assign_label(label)
                db.session.commit()
                flash(_("The label has been successfully created."), 'info')
                return redirect(self.obj.project.url_for('labelsets'), code=303)
            else:
                flash(_("You don't have permission to create a new label for this project"), 'danger')
                return redirect(self.obj.project.url_for('labelsets'), code=303)
        return render_form(form=form, title=_("New label for '{}'".format(self.obj.title)), submit=_("Create label"))


@route('/<project>/labelset/<labelset>', subdomain='<profile>')
class FunnelLabelsetView(LabelsetView):
    pass


LabelsetView.init_app(app)
FunnelLabelsetView.init_app(funnelapp)


@route('/<profile>/<project>/labelset/<labelset>/labels/<label>')
class LabelView(UrlForView, ModelView):
    __decorators__ = [lastuser.requires_login, legacy_redirect]
    model = Label
    route_model_map = {
        'profile': 'labelset.project.profile.name', 'project': 'labelset.project.name',
        'labelset': 'labelset.name', 'label': 'name'}

    def loader(self, profile, project, labelset, label):
        label = self.model.query.join(Labelset.project).filter(
            Project.name == project,
            Labelset.name == labelset, Label.name == label
            ).first_or_404()
        g.profile = label.labelset.project.profile
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
            return redirect(self.obj.labelset.project.url_for('labelsets'), code=303)
        return render_form(form=form, title=_("Edit label"), submit=_("Save changes"))

    @route('delete', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
    def delete(self):
        return render_delete_sqla(self.obj, db, title=_(u"Confirm delete"),
            message=_(u"Do you really wish to delete label '{title}’?").format(title=self.obj.title),
            success=_("Your label has been deleted"),
            next=self.obj.labelset.project.url_for('labelsets'),
            cancel_url=self.obj.labelset.project.url_for('labelsets'))


@route('/<project>/labelset/<label>', subdomain='<profile>')
class FunnelLabelView(LabelView):
    pass


LabelView.init_app(app)
FunnelLabelView.init_app(funnelapp)
