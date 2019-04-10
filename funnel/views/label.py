# -*- coding: utf-8 -*-

from flask import flash, redirect
from coaster.views import render_with, requires_permission, route, UrlForView, ModelView
from baseframe import _
from baseframe.forms import render_delete_sqla, render_form

from .. import app, funnelapp, lastuser
from ..models import Labelset, Label, db
from ..forms import LabelsetForm, LabelForm
from .mixins import ProjectViewMixin
from .decorators import legacy_redirect


@route('/<profile>/<project>/labelset')
class ProjectLabelsetView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('labels.html.jinja2')
    @lastuser.requires_login
    @requires_permission('edit_project')
    def labelset(self):
        return dict(project=self.obj, labelsets=self.obj.labelsets)

    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_projeckt')
    def new_labelset(self):
        form = LabelsetForm(model=Labelset, parent=self.obj)
        return render_form(form=form, title=_("New labelset"), submit=_("Create labelset"))

    @route('edit', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
    def edit_labelset(self):
        form = LabelsetForm(obj=self.obj, model=Labelset, parent=self.obj.parent)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your labelset has been edited"), 'info')
            return redirect(self.obj.project.url_for('labelset'), code=303)
        return render_form(form=form, title=_("Edit labelset"), submit=_("Save changes"))

    @route('delete', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
    def delete_labelset(self):
        return render_delete_sqla(self.obj, db, title=_(u"Confirm delete"),
            message=_(u"Do you really wish to delete labelset '{title}’?").format(title=self.obj.title),
            success=_("Your labelset has been deleted"),
            next=self.obj.project.url_for('sections'),
            cancel_url=self.obj.project.url_for('labelset'))


@route('/<project>/labelset', subdomain='<profile>')
class FunnelProjectLabelsetView(ProjectLabelsetView):
    pass


ProjectLabelsetView.init_app(app)
FunnelProjectLabelsetView.init_app(funnelapp)


@route('/<profile>/<project>/labelset/<label>')
class LabelView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [lastuser.requires_login, legacy_redirect]

    @route('edit', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
    def edit_label(self):
        form = LabelForm(obj=self.obj, model=Label, parent=self.obj.parent)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your labelset has been edited"), 'info')
            return redirect(self.obj.project.url_for('labelset'), code=303)
        return render_form(form=form, title=_("Edit label"), submit=_("Save changes"))

    @route('delete', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
    def delete_label(self):
        return render_delete_sqla(self.obj, db, title=_(u"Confirm delete"),
            message=_(u"Do you really wish to delete label '{title}’?").format(title=self.obj.title),
            success=_("Your label has been deleted"),
            next=self.obj.project.url_for('sectns'),
            cancel_url=self.obj.project.url_for('labelset'))


@route('/<project>/labelset/<label>', subdomain='<profile>')
class FunnelLabelView(LabelView):
    pass


LabelView.init_app(app)
FunnelLabelView.init_app(funnelapp)
