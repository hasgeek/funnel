from __future__ import annotations

from typing import Optional

from flask import abort, flash, redirect

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
from ..models import NewUpdateNotification, Profile, Project, Update, db
from ..typing import ReturnView
from .helpers import html_in_json
from .login_session import requires_login, requires_sudo
from .mixins import ProfileCheckMixin
from .notification import dispatch_notification
from .project import ProjectViewMixin


@Project.views('updates')
@route('/<profile>/<project>/updates')
class ProjectUpdatesView(ProjectViewMixin, UrlChangeCheck, UrlForView, ModelView):
    @route('', methods=['GET'])
    @render_with(html_in_json('project_updates.html.jinja2'))
    @requires_roles({'reader'})
    def updates(self):
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
    def new_update(self):
        form = UpdateForm()

        if form.validate_on_submit():
            update = Update(user=current_auth.user, project=self.obj)
            form.populate_obj(update)
            update.name = make_name(update.title)
            db.session.add(update)
            db.session.commit()
            return redirect(update.url_for(), code=303)

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
@route('/<profile>/<project>/updates/<update>')
class UpdateView(ProfileCheckMixin, UrlChangeCheck, UrlForView, ModelView):
    model = Update
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'update': 'url_name_uuid_b58',
    }
    obj: Update
    SavedProjectForm = SavedProjectForm

    def loader(self, profile, project, update) -> Update:
        return (
            Update.query.join(Project)
            .join(Profile, Project.profile_id == Profile.id)
            .filter(Update.url_name_uuid_b58 == update)
            .one_or_404()
        )

    def after_loader(self) -> Optional[ReturnView]:
        self.profile = self.obj.project.profile
        return super().after_loader()

    @route('', methods=['GET'])
    @render_with('update_details.html.jinja2')
    def view(self):
        if not self.obj.current_roles.reader and self.obj.state.WITHDRAWN:
            abort(410)
        return {
            'update': self.obj.current_access(datasets=('primary', 'related')),
            'publish_form': forms.Form(),
            'project': self.obj.project.current_access(),
        }

    @route('publish', methods=['POST'])
    @requires_roles({'editor'})
    def publish(self):
        if not self.obj.state.DRAFT:
            return redirect(self.obj.url_for())
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
        return redirect(self.obj.project.url_for('updates'))

    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_roles({'editor'})
    def edit(self):
        form = UpdateForm(obj=self.obj)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("The update has been edited"), 'success')
            return redirect(self.obj.url_for(), code=303)

        return render_form(
            form=form,
            title=_("Edit update"),
            submit=_("Save"),
            cancel_url=self.obj.url_for(),
        )

    @route('delete', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_sudo
    @requires_roles({'editor'})
    def delete(self):
        form = forms.Form()

        if form.validate_on_submit():
            self.obj.delete(actor=current_auth.user)
            db.session.commit()
            flash(_("The update has been deleted"), 'success')
            return redirect(self.obj.project.url_for('updates'))

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
