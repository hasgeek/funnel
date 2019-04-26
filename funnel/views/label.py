# -*- coding: utf-8 -*-

from flask import flash, redirect, g, request
from werkzeug.datastructures import MultiDict
from coaster.views import render_with, requires_permission, route, UrlForView, ModelView
from baseframe import _, forms

from .. import app, funnelapp, lastuser
from ..models import Label, db, Project, Profile
from ..forms import LabelForm, LabelOptionForm
from .mixins import ProjectViewMixin
from .decorators import legacy_redirect


@route('/<profile>/<project>/labels')
class ProjectLabelView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('', methods=['GET', 'POST'])
    @render_with('labels.html.jinja2')
    @lastuser.requires_login
    @requires_permission('edit_project')
    def labels(self):
        form = forms.Form()
        if form.validate_on_submit():
            namelist = request.values.getlist('name')
            for idx, lname in enumerate(namelist, start=1):
                lbl = Label.query.filter_by(project=self.obj, name=lname).first()
                if lbl is not None:
                    lbl.seq = idx
                    db.session.commit()
            flash(_("Your changes have been saved"), category='success')
        return dict(project=self.obj, labels=self.obj.labels, form=form)

    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @render_with('labels_form.html.jinja2')
    @requires_permission('admin')
    def new_label(self):
        form = LabelForm(model=Label, parent=self.obj.parent)
        emptysubform = LabelOptionForm(MultiDict({}))
        if form.validate_on_submit():
            # This form can send one or multiple values for title and icon_emoji.
            # If the label doesn't have any options, one value is sent for each list,
            # and those values are also available at `form.data`.
            # But in case there are options, the option values are in the list
            # in the order they appeared on the create form.
            titlelist = request.values.getlist('title')
            emojilist = request.values.getlist('icon_emoji')
            # first values of both lists belong to the parent label
            titlelist.pop(0)
            emojilist.pop(0)

            label = Label(title=form.data.get('title'), icon_emoji=form.data.get('icon_emoji'), project=self.obj)
            label.restricted = form.data.get('restricted')
            label.make_name()
            self.obj.labels.append(label)
            self.obj.labels.reorder()
            db.session.add(label)

            for idx, title in enumerate(titlelist):
                subform = LabelOptionForm(MultiDict({
                    'title': titlelist[idx], 'icon_emoji': emojilist[idx]
                }), meta={'csrf': False})  # parent form has valid CSRF token

                if not subform.validate():
                    flash(_("Error with a label option: {}").format(subform.errors.pop()), category='error')
                    return dict(title="Add label", form=form, project=self.obj)
                else:
                    subl = Label(project=self.obj)
                    subform.populate_obj(subl)
                    subl.make_name()
                    db.session.add(subl)
                    label.options.append(subl)

            db.session.commit()
            return redirect(self.obj.url_for('labels'), code=303)
        return dict(title="Add label", form=form, emptysubform=emptysubform, project=self.obj)


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
        g.profile = proj.profile
        return label

    @route('edit', methods=['GET', 'POST'])
    @lastuser.requires_login
    @render_with('labels_form.html.jinja2')
    @requires_permission('edit_project')
    def edit(self):
        emptysubform = LabelOptionForm(MultiDict({}))
        subforms = []
        if self.obj.is_main_label:
            form = LabelForm(obj=self.obj, model=Label, parent=self.obj.project)
            if self.obj.has_options:
                for subl in self.obj.options:
                    subforms.append(LabelOptionForm(obj=subl, parent=self.obj.project))
        else:
            flash(_("Only main labels can be edited"), category='error')
            return redirect(self.obj.project.url_for('labels'), code=303)

        if form.validate_on_submit():
            namelist = request.values.getlist('name')
            titlelist = request.values.getlist('title')
            emojilist = request.values.getlist('icon_emoji')

            namelist.pop(0)
            titlelist.pop(0)
            emojilist.pop(0)

            for idx, title in enumerate(titlelist):
                if namelist[idx]:
                    # existing option
                    subl = Label.query.filter_by(project=self.obj.project, name=namelist[idx]).first()
                    subl.title = titlelist[idx]
                    subl.icon_emoji = emojilist[idx]
                    subl.seq = idx + 1
                else:
                    subform = LabelOptionForm(MultiDict({
                        'title': titlelist[idx], 'icon_emoji': emojilist[idx]
                    }), meta={'csrf': False})  # parent form has valid CSRF token

                    if not subform.validate():
                        flash(_("Error with a label option: {}").format(subform.errors.pop()), category='error')
                        return dict(title="Edit label", form=form, project=self.obj.project)
                    else:
                        subl = Label(project=self.obj.project)
                        subform.populate_obj(subl)
                        subl.make_name()
                        self.obj.project.labels.append(subl)
                        self.obj.options.append(subl)
                        self.obj.options.reorder()
                        db.session.add(subl)

            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Label has been edited"), category='success')

            return redirect(self.obj.project.url_for('labels'), code=303)
        return dict(title="Edit label", form=form, subforms=subforms, emptysubform=emptysubform, project=self.obj.project)

    @route('archive', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('admin')
    def archive(self):
        form = forms.Form()
        if form.validate_on_submit():
            self.obj.archived = True
            db.session.commit()
            flash(_("The label has been archived"), category='success')
        else:
            flash(_("CSRF token is missing"), category='error')
        return redirect(self.obj.project.url_for('labels'), code=303)

    @route('delete', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('admin')
    def delete(self):
        if self.obj.has_proposals:
            flash(_("Labels that have been assigned to proposals cannot be deleted"), category='error')
        else:
            if self.obj.has_options:
                for olabel in self.obj.options:
                    db.session.delete(olabel)
            db.session.delete(self.obj)
            db.session.commit()

            if self.obj.main_label:
                self.obj.main_label.options.reorder()
                db.session.commit()
            flash(_("The label has been deleted"), category='success')
        return redirect(self.obj.project.url_for('labels'), code=303)


@route('/<project>/labels/<label>', subdomain='<profile>')
class FunnelLabelView(LabelView):
    pass


LabelView.init_app(app)
FunnelLabelView.init_app(funnelapp)
