from __future__ import annotations

from flask import flash, redirect, request
from werkzeug.datastructures import MultiDict

from baseframe import _, forms
from coaster.views import ModelView, UrlForView, render_with, requires_roles, route

from .. import app
from ..forms import LabelForm, LabelOptionForm
from ..models import Label, Profile, Project, db
from ..utils import abort_null
from .login_session import requires_login, requires_sudo
from .mixins import ProfileCheckMixin, ProjectViewMixin


@Project.views('label')
@route('/<profile>/<project>/labels')
class ProjectLabelView(ProjectViewMixin, UrlForView, ModelView):
    @route('', methods=['GET', 'POST'])
    @render_with('labels.html.jinja2')
    @requires_login
    @requires_roles({'editor'})
    def labels(self):
        form = forms.Form()
        if form.validate_on_submit():
            namelist = [abort_null(x) for x in request.values.getlist('name')]
            for idx, lname in enumerate(namelist, start=1):
                lbl = Label.query.filter_by(project=self.obj, name=lname).first()
                if lbl is not None:
                    lbl.seq = idx
                    db.session.commit()
            flash(_("Your changes have been saved"), category='success')
        return {'project': self.obj, 'labels': self.obj.labels, 'form': form}

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @render_with('labels_form.html.jinja2')
    @requires_roles({'editor'})
    def new_label(self):
        form = LabelForm(model=Label, parent=self.obj.parent)
        emptysubform = LabelOptionForm(MultiDict({}))
        if form.validate_on_submit():
            # This form can send one or multiple values for title and icon_emoji.
            # If the label doesn't have any options, one value is sent for each list,
            # and those values are also available at `form.data`.
            # But in case there are options, the option values are in the list
            # in the order they appeared on the create form.
            titlelist = [abort_null(x) for x in request.values.getlist('title')]
            emojilist = [abort_null(x) for x in request.values.getlist('icon_emoji')]
            # first values of both lists belong to the parent label
            titlelist.pop(0)
            emojilist.pop(0)

            label = Label(
                title=form.data.get('title'),
                icon_emoji=form.data.get('icon_emoji'),
                project=self.obj,
            )
            label.restricted = form.data.get('restricted')
            label.make_name()
            self.obj.all_labels.append(label)
            self.obj.all_labels.reorder()

            for idx in range(len(titlelist)):
                subform = LabelOptionForm(
                    MultiDict({'title': titlelist[idx], 'icon_emoji': emojilist[idx]}),
                    meta={'csrf': False},
                )  # parent form has valid CSRF token

                if not subform.validate():
                    flash(
                        _("Error with a label option: {}").format(subform.errors.pop()),
                        category='error',
                    )
                    return {'title': "Add label", 'form': form, 'project': self.obj}
                else:
                    subl = Label(project=self.obj)
                    subform.populate_obj(subl)
                    subl.make_name()
                    db.session.add(subl)
                    label.options.append(subl)

            db.session.commit()
            return redirect(self.obj.url_for('labels'), code=303)
        return {
            'title': "Add label",
            'form': form,
            'emptysubform': emptysubform,
            'project': self.obj,
        }


ProjectLabelView.init_app(app)


@Label.views('main')
@route('/<profile>/<project>/labels/<label>')
class LabelView(ProfileCheckMixin, UrlForView, ModelView):
    __decorators__ = [requires_login]
    model = Label
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'label': 'name',
    }

    def loader(self, profile, project, label):
        proj = (
            Project.query.join(Profile)
            .filter(
                db.func.lower(Profile.name) == db.func.lower(profile),
                Project.name == project,
            )
            .first_or_404()
        )
        label = self.model.query.filter_by(project=proj, name=label).first_or_404()
        return label

    def after_loader(self):
        self.profile = self.obj.project.profile
        return super().after_loader()

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @render_with('labels_form.html.jinja2')
    @requires_roles({'project_editor'})
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
            namelist = [abort_null(x) for x in request.values.getlist('name')]
            titlelist = [abort_null(x) for x in request.values.getlist('title')]
            emojilist = [abort_null(x) for x in request.values.getlist('icon_emoji')]

            namelist.pop(0)
            titlelist.pop(0)
            emojilist.pop(0)

            for idx in range(len(titlelist)):
                if namelist[idx]:
                    # existing option
                    subl = Label.query.filter_by(
                        project=self.obj.project, name=namelist[idx]
                    ).first()
                    subl.title = titlelist[idx]
                    subl.icon_emoji = emojilist[idx]
                    subl.seq = idx + 1
                else:
                    subform = LabelOptionForm(
                        MultiDict(
                            {'title': titlelist[idx], 'icon_emoji': emojilist[idx]}
                        ),
                        meta={'csrf': False},
                    )  # parent form has valid CSRF token

                    if not subform.validate():
                        flash(
                            _("Error with a label option: {}").format(
                                subform.errors.pop()
                            ),
                            category='error',
                        )
                        return {
                            'title': "Edit label",
                            'form': form,
                            'project': self.obj.project,
                        }
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
        return {
            'title': "Edit label",
            'form': form,
            'subforms': subforms,
            'emptysubform': emptysubform,
            'project': self.obj.project,
        }

    @route('archive', methods=['POST'])
    @requires_login
    @requires_roles({'project_editor'})
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
    @requires_sudo
    @requires_roles({'project_editor'})
    def delete(self):
        if self.obj.has_proposals:
            flash(
                _("Labels that have been assigned to submissions cannot be deleted"),
                category='error',
            )
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


LabelView.init_app(app)
