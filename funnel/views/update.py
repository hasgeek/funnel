"""Views for updates in a project."""

from __future__ import annotations

from flask import abort, flash

from baseframe import _, forms
from baseframe.forms import render_form
from coaster.auth import current_auth
from coaster.utils import make_name
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    render_with,
    requires_roles,
    route,
)

from .. import app
from ..forms import SavedProjectForm, UpdateForm
from ..models import Account, NewUpdateNotification, Project, Update, db
from ..typing import ReturnRenderWith, ReturnView
from .helpers import html_in_json, render_redirect
from .login_session import requires_login, requires_sudo
from .mixins import AccountCheckMixin
from .notification import dispatch_notification
from .project import ProjectViewBase


@Project.views('updates')
@route('/<account>/<project>/updates')
class ProjectUpdatesView(UrlChangeCheck, UrlForView, ProjectViewBase):
    @route('', methods=['GET'])
    @render_with(html_in_json('project_updates.html.jinja2'))
    @requires_roles({'reader'})
    def updates(self) -> ReturnRenderWith:
        project = self.obj.current_access(datasets=('primary', 'related'))
        draft_updates = (
            [
                update.current_access(datasets=('without_parent', 'related'))
                for update in self.obj.draft_updates
            ]
            if self.obj.features.post_update()
            else []
        )
        published_updates = [
            update.current_access(datasets=('without_parent', 'related'))
            for update in self.obj.published_updates
        ]
        new_update = self.obj.url_for('new_update')
        return {
            'project': project,
            'draft_updates': draft_updates,
            'published_updates': published_updates,
            'new_update': new_update,
        }

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def new_update(self) -> ReturnView:
        form = UpdateForm()

        if form.validate_on_submit():
            update = Update(created_by=current_auth.user, project=self.obj)
            form.populate_obj(update)
            update.name = make_name(update.title)
            db.session.add(update)
            db.session.commit()
            return render_redirect(update.url_for())

        return render_form(
            form=form,
            title=_("Post an update"),
            submit=_("Save & preview"),
            cancel_url=self.obj.url_for('updates'),
        )


ProjectUpdatesView.init_app(app)


@Update.features('publish')
def update_publishable(obj):
    return obj.state.DRAFT and 'editor' in obj.roles_for(current_auth.user)


@Update.views('project')
@route('/<account>/<project>/updates/<update>')
class UpdateView(AccountCheckMixin, UrlChangeCheck, UrlForView, ModelView[Update]):
    route_model_map = {
        'account': 'project.account.urlname',
        'project': 'project.name',
        'update': 'url_name_uuid_b58',
    }
    SavedProjectForm = SavedProjectForm

    def load(self, account: str, project: str, update: str) -> ReturnView | None:
        self.obj = (
            Update.query.join(Project)
            .join(Account, Project.account)
            .filter(Update.url_name_uuid_b58 == update)
            .one_or_404()
        )
        self.post_init()
        return super().after_loader()

    def post_init(self) -> None:
        self.account = self.obj.project.account

    @route('', methods=['GET'])
    @render_with('update_details.html.jinja2')
    def view(self) -> ReturnRenderWith:
        if not self.obj.current_roles.reader and self.obj.state.WITHDRAWN:
            abort(410)
        return {
            'update': self.obj.current_access(datasets=('primary', 'related')),
            'publish_form': forms.Form(),
            'project': self.obj.project.current_access(),
        }

    @route('publish', methods=['POST'])
    @requires_roles({'editor'})
    def publish(self) -> ReturnView:
        if not self.obj.state.DRAFT:
            return render_redirect(self.obj.url_for())
        form = forms.Form()
        if form.validate_on_submit():
            first_publishing = self.obj.publish(actor=current_auth.user)
            db.session.commit()
            flash(_("The update has been published"), 'success')
            if first_publishing:
                dispatch_notification(NewUpdateNotification(document=self.obj))
        else:
            flash(
                _("There was an error publishing this update. Reload and try again"),
                'error',
            )
        return render_redirect(self.obj.project.url_for('updates'))

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'editor'})
    def edit(self) -> ReturnView:
        form = UpdateForm(obj=self.obj)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("The update has been edited"), 'success')
            return render_redirect(self.obj.url_for())

        return render_form(
            form=form,
            title=_("Edit update"),
            submit=_("Save"),
            cancel_url=self.obj.url_for(),
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'editor'})
    def delete(self) -> ReturnView:
        form = forms.Form()

        if form.validate_on_submit():
            self.obj.delete(actor=current_auth.user)
            db.session.commit()
            flash(_("The update has been deleted"), 'success')
            return render_redirect(self.obj.project.url_for('updates'))

        return render_form(
            form=form,
            title=_("Confirm delete"),
            message=_(
                "Delete this draft update? This operation is permanent and cannot be"
                " undone"
            )
            if self.obj.state.UNPUBLISHED
            else _(
                "Delete this update? This update’s number (#{number}) will be skipped"
                " for the next update"
            ).format(number=self.obj.number),
            submit=_("Delete"),
            cancel_url=self.obj.url_for(),
        )


UpdateView.init_app(app)
