"""Workflow label views."""

from __future__ import annotations

from flask import flash, request
from werkzeug.datastructures import MultiDict

from baseframe import _, forms
from baseframe.forms import render_form
from coaster.views import ModelView, UrlForView, render_with, requires_roles, route

from .. import app
from ..forms import LabelForm, LabelOptionForm
from ..models import Account, Label, Project, db
from ..typing import ReturnRenderWith, ReturnView
from .helpers import render_redirect
from .login_session import requires_login, requires_sudo
from .mixins import AccountCheckMixin, ProjectViewBase


@Project.views('label')
@route('/<account>/<project>/labels', init_app=app)
class ProjectLabelView(ProjectViewBase):
    @route('', methods=['GET', 'POST'])
    @render_with('labels.html.jinja2')
    @requires_login
    @requires_roles({'editor'})
    def labels(self) -> ReturnRenderWith:
        form = forms.Form()
        if form.validate_on_submit():
            namelist = request.values.getlist('name')
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
    def new_label(self) -> ReturnRenderWith:
        form = LabelForm(model=Label, parent=self.obj.parent)
        emptysubform = LabelOptionForm(MultiDict({}))
        if form.validate_on_submit():
            # This form can send one or multiple values for title and icon_emoji.
            # If the label doesn't have any options, one value is sent for each list,
            # and those values are also available at `form.data`.
            # But in case there are options, the option values are in the list
            # in the order they appeared on the create form.
            titlelist = request.form.getlist('title')
            emojilist = request.form.getlist('icon_emoji')
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

            for title, emoji in zip(titlelist, emojilist, strict=True):
                subform = LabelOptionForm(
                    MultiDict({'title': title, 'icon_emoji': emoji}),
                    # parent form has valid CSRF token
                    meta={'csrf': False},
                )

                if not subform.validate():
                    flash(
                        _("Error with a label option: {}").format(subform.errors.pop()),
                        category='error',
                    )
                    return {'title': _("Add label"), 'form': form, 'project': self.obj}
                subl = Label(project=self.obj)
                subform.populate_obj(subl)
                subl.make_name()
                db.session.add(subl)
                label.options.append(subl)

            db.session.commit()
            return render_redirect(self.obj.url_for('labels'))
        return {
            'title': _("Add label"),
            'form': form,
            'emptysubform': emptysubform,
            'project': self.obj,
            'ref_id': 'form-labels',
        }


@Label.views('main')
@route('/<account>/<project>/labels/<label>', init_app=app)
class LabelView(AccountCheckMixin, UrlForView, ModelView[Label]):
    __decorators__ = [requires_login]
    route_model_map = {
        'account': 'project.account.urlname',
        'project': 'project.name',
        'label': 'name',
    }

    def loader(self, account: str, project: str, label: str) -> Label:
        return (
            Label.query.join(Project, Label.project)
            .join(Account, Project.account)
            .filter(
                Account.name_is(account), Project.name == project, Label.name == label
            )
            .first_or_404()
        )

    @property
    def account(self) -> Account:
        return self.obj.project.account

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @render_with('labels_form.html.jinja2')
    @requires_roles({'project_editor'})
    def edit(self) -> ReturnRenderWith:
        emptysubform = LabelOptionForm(MultiDict({}))
        subforms: list[LabelOptionForm] = []
        if self.obj.is_main_label:
            form = LabelForm(obj=self.obj, model=Label, parent=self.obj.project)
            if self.obj.has_options:
                subforms.extend(
                    LabelOptionForm(obj=subl, parent=self.obj.project)
                    for subl in self.obj.options
                )
        else:
            flash(_("Only main labels can be edited"), category='error')
            return render_redirect(self.obj.project.url_for('labels'))

        if form.validate_on_submit():
            namelist = request.form.getlist('name')
            titlelist = request.form.getlist('title')
            emojilist = request.form.getlist('icon_emoji')

            namelist.pop(0)
            titlelist.pop(0)
            emojilist.pop(0)

            for counter, (name, title, emoji) in enumerate(
                zip(namelist, titlelist, emojilist, strict=True)
            ):
                if name:
                    # existing option
                    subl = Label.query.filter_by(
                        project=self.obj.project, name=name
                    ).one()
                    subl.title = title
                    subl.icon_emoji = emoji
                    subl.seq = counter + 1  # Counter is 0-indexed, seq is 1-indexed
                else:
                    subform = LabelOptionForm(
                        MultiDict({'title': title, 'icon_emoji': emoji}),
                        # parent form has valid CSRF token
                        meta={'csrf': False},
                    )

                    if not subform.validate():
                        flash(
                            _("Error with a label option: {}").format(
                                subform.errors.pop()
                            ),
                            category='error',
                        )
                        return {
                            'title': _("Edit label"),
                            'form': form,
                            'project': self.obj.project,
                        }
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

            return render_redirect(self.obj.project.url_for('labels'))
        return {
            'title': _("Edit label"),
            'form': form,
            'ref_id': 'form-labels',
            'subforms': subforms,
            'emptysubform': emptysubform,
            'project': self.obj.project,
        }

    @route('archive', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'project_editor'})
    def archive(self) -> ReturnView:
        form = forms.Form()
        if form.validate_on_submit():
            self.obj.archived = True
            db.session.commit()
            flash(_("The label has been archived"), category='success')
            return render_redirect(self.obj.project.url_for('labels'))
        return render_form(
            form=form,
            title=_("Confirm archive of label"),
            message=_("Archive this label?"),
            submit=_("Archive"),
            cancel_url=self.obj.project.url_for('labels'),
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'project_editor'})
    def delete(self) -> ReturnView:
        form = forms.Form()

        if form.validate_on_submit():
            if self.obj.has_proposals:
                flash(
                    _(
                        "Labels that have been assigned to submissions cannot be"
                        " deleted"
                    ),
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
            return render_redirect(self.obj.project.url_for('labels'))
        return render_form(
            form=form,
            title=_("Confirm delete"),
            message=_(
                "Delete this label? This operation is permanent and cannot be undone"
            ),
            submit=_("Delete"),
            cancel_url=self.obj.project.url_for('labels'),
        )
