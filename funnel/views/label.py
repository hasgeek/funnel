# -*- coding: utf-8 -*-

from flask import flash, redirect, g, render_template, request
from werkzeug.datastructures import MultiDict
from coaster.views import render_with, requires_permission, route, UrlForView, ModelView
from baseframe import _
from baseframe.forms import render_delete_sqla, render_form

from .. import app, funnelapp, lastuser
from ..models import Label, db, Project, Profile
from ..forms import LabelForm, SublabelForm
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
    @render_with('labels_form.html.jinja2')
    @requires_permission('admin')
    def new_label(self):
        form = LabelForm(model=Label, parent=self.obj.parent)
        emptysubform = SublabelForm(MultiDict({}))
        if form.validate_on_submit():
            # This form can send one or multiple values for title and icon_emoji.
            # If the label doesn't have any sublabel, one value is sent for each list,
            # and those values are also available at `form.data`.
            # But in case there are sublabels, the sublabel values are in the list
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
            db.session.add(label)

            for idx, title in enumerate(titlelist):
                subform = SublabelForm(MultiDict({
                    'csrf_token': form.csrf_token.data, 'title': titlelist[idx],
                    'icon_emoji': emojilist[idx]
                    }))

                if not subform.validate():
                    flash(_("Error with a sublabel: {}").format(subform.errors.pop()), category='error')
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
        g.profile = label.project.profile
        return label

    @route('edit', methods=['GET', 'POST'])
    @lastuser.requires_login
    @render_with('labels_form.html.jinja2')
    @requires_permission('edit_project')
    def edit(self):
        emptysubform = SublabelForm(MultiDict({}))
        subforms = []
        if self.obj.main_label:
            # It's a sublabel
            form = SublabelForm(obj=self.obj, model=Label, parent=self.obj.project)
        else:
            form = LabelForm(obj=self.obj, model=Label, parent=self.obj.project)
            if self.obj.is_main:
                for subl in self.obj.options:
                    subforms.append(SublabelForm(obj=subl, parent=self.obj.project))

        if form.validate_on_submit():
            form.populate_obj(self.obj)

            idlist = request.values.getlist('id')
            titlelist = request.values.getlist('title')
            emojilist = request.values.getlist('icon_emoji')

            idlist.pop(0)
            titlelist.pop(0)
            emojilist.pop(0)

            for idx, title in enumerate(titlelist):
                if idlist[idx]:
                    # existing sublabel
                    subl = Label.query.filter_by(project=self.obj.project, id=idlist[idx]).first()
                    subl.title = titlelist[idx]
                    subl.icon_emoji = emojilist[idx]
                else:
                    subform = SublabelForm(MultiDict({
                        'csrf_token': form.csrf_token.data, 'title': titlelist[idx],
                        'icon_emoji': emojilist[idx]
                        }))

                    if not subform.validate():
                        flash(_("Error with a sublabel: {}").format(subform.errors.pop()), category='error')
                        return dict(title="Edit label", form=form, project=self.obj.project)
                    else:
                        subl = Label(project=self.obj.project)
                        subform.populate_obj(subl)
                        subl.make_name()
                        self.obj.project.labels.append(subl)
                        self.obj.options.append(subl)
                        db.session.add(subl)

            db.session.commit()
            return redirect(self.obj.project.url_for('labels'), code=303)
        return dict(title="Edit label", form=form, subforms=subforms, emptysubform=emptysubform, project=self.obj.project)

    @route('archive', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('admin')
    def archive(self):
        return redirect(self.obj.project.url_for('labels'), code=303)


@route('/<project>/labels/<label>', subdomain='<profile>')
class FunnelLabelView(LabelView):
    pass


LabelView.init_app(app)
FunnelLabelView.init_app(funnelapp)
