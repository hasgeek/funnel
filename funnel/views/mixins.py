"""Mixins for model views."""
# TODO: Move each mixin into the main file for each view, or into <model>_mixin.py

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from flask import abort, g, request
from werkzeug.datastructures import MultiDict

from baseframe import _, forms
from coaster.auth import current_auth
from coaster.views import ModelView, UrlChangeCheck, UrlForView, route

from ..forms import SavedProjectForm
from ..models import (
    Account,
    Draft,
    Project,
    ProjectRedirect,
    TicketEvent,
    UuidModelUnion,
    db,
)
from ..typing import ReturnView
from .helpers import render_redirect
from .login_session import requires_login


class AccountCheckMixin:
    """Base class checks for suspended accounts."""

    account: Account

    def after_loader(self) -> ReturnView | None:
        """Post-process loader."""
        account = self.account
        g.account = account
        if not account.state.ACTIVE:
            abort(410)

        # mypy doesn't know this is a mixin, so it warns that `after_loader` is not
        # defined in the superclass. We ask it to ignore the problem here instead of
        # creating an elaborate workaround using `typing.TYPE_CHECKING`.
        # https://github.com/python/mypy/issues/5837
        return super().after_loader()  # type: ignore[misc]


class ProjectViewBase(
    AccountCheckMixin, UrlForView, UrlChangeCheck, ModelView[Project]
):
    route_model_map = {'account': 'account.urlname', 'project': 'name'}
    SavedProjectForm = SavedProjectForm
    CsrfForm = forms.Form
    project: Project

    def load(self, account: str, project: str, **_kwargs) -> ReturnView | None:
        obj = (
            Project.query.join(Account, Project.account)
            .filter(Account.name_is(account), Project.name == project)
            .first()
        )
        if obj is None:
            obj_redirect = (
                ProjectRedirect.query.join(Account, ProjectRedirect.account)
                .filter(Account.name_is(account), ProjectRedirect.name == project)
                .first_or_404()
            )
            if obj_redirect.project:
                self.account = obj_redirect.project.account
                return render_redirect(
                    obj_redirect.project.url_for(),
                    302 if request.method == 'GET' else 303,
                )
            abort(410)  # Project has been deleted
        elif obj.state.DELETED:
            abort(410)
        self.obj = obj
        self.post_init()
        return self.after_loader()

    def post_init(self) -> None:
        self.project = project = self.obj
        self.account = project.account

    @property
    def project_currently_saved(self):
        return self.obj.is_saved_by(current_auth.user)


class AccountViewBase(AccountCheckMixin, UrlForView, ModelView[Account]):
    route_model_map = {'account': 'urlname'}
    SavedProjectForm = SavedProjectForm
    CsrfForm = forms.Form

    def loader(self, account: str) -> Account:
        obj = Account.get(name=account)
        if obj is None:
            abort(404)
        return obj

    def post_init(self) -> None:
        self.account = self.obj


@route('/<account>/<project>/ticket_event/<name>')
class TicketEventViewBase(AccountCheckMixin, UrlForView, ModelView[TicketEvent]):
    __decorators__ = [requires_login]
    route_model_map = {
        'account': 'project.account.urlname',
        'project': 'project.name',
        'name': 'name',
    }

    def loader(self, account: str, project: str, name: str) -> TicketEvent:
        return (
            TicketEvent.query.join(Project)
            .join(Account, Project.account)
            .filter(
                Account.name_is(account),
                Project.name == project,
                TicketEvent.name == name,
            )
            .one_or_404()
        )

    def post_init(self) -> None:
        self.account = self.obj.project.account


class DraftViewProtoMixin:
    model: Any
    obj: Any

    def get_draft(self, obj: UuidModelUnion | None = None) -> Draft | None:
        """
        Return the draft object for `obj`. Defaults to `self.obj`.

        `obj` is needed in case of multi-model views.
        """
        obj = obj if obj is not None else self.obj
        return Draft.query.get((self.model.__tablename__, obj.uuid))

    def delete_draft(self, obj=None):
        """Delete draft for `obj`, or `self.obj` if `obj` is `None`."""
        draft = self.get_draft(obj)
        if draft is not None:
            db.session.delete(draft)
        else:
            raise ValueError(_("There is no draft for the given object"))

    def get_draft_data(
        self, obj: UuidModelUnion | None = None
    ) -> tuple[None, None] | tuple[UUID | None, dict]:
        """
        Return a tuple of draft data.

        Contains the current draft revision and the formdata needed to initialize forms.
        """
        draft = self.get_draft(obj)
        if draft is not None:
            return draft.revision, draft.formdata
        return None, None

    def autosave_post(self, obj: UuidModelUnion | None = None) -> ReturnView:
        """Handle autosave POST requests."""
        obj = obj if obj is not None else self.obj
        if 'form.revision' not in request.form:
            # as form.autosave is true, the form should have `form.revision` field even
            # if it's empty
            return (
                {
                    'status': 'error',
                    'error': 'form_missing_revision_field',
                    'error_description': _("Form must contain a revision ID"),
                },
                400,
            )

        # CSRF check
        form = forms.Form()
        if form.validate_on_submit():
            incoming_data: MultiDict = MultiDict(request.form.items(multi=True))
            client_revision = incoming_data.pop('form.revision')
            incoming_data.pop('csrf_token', None)
            incoming_data.pop('form_nonce', None)

            # find the last draft
            draft = self.get_draft(obj)

            if draft is None and client_revision:
                # The form contains a revision ID but no draft exists.
                # Somebody is making autosave requests with an invalid draft ID.
                return (
                    {
                        'status': 'error',
                        'error': 'invalid_or_expired_revision',
                        'error_description': _(
                            "Invalid revision ID or the existing changes have been"
                            " submitted already. Please reload"
                        ),
                    },
                    400,
                )
            if draft is not None:
                if client_revision is None or (
                    client_revision is not None
                    and str(draft.revision) != client_revision
                ):
                    # draft exists, but the form did not send a revision ID,
                    # OR revision ID sent by client does not match the last revision ID
                    return (
                        {
                            'status': 'error',
                            'error': 'missing_or_invalid_revision',
                            'error_description': _(
                                "There have been changes to this draft since you last"
                                " edited it. Please reload"
                            ),
                        },
                        400,
                    )
                if (
                    client_revision is not None
                    and str(draft.revision) == client_revision
                ):
                    # revision ID sent by client matches, save updated draft data and
                    # update revision ID. Since `formdata` is a `MultiDict`, we cannot
                    # use `formdata.update`. The behaviour is different
                    draft.formdata.update(incoming_data)
                    existing = draft.formdata
                    for key, value in incoming_data.items():
                        if existing[key] != value:
                            existing[key] = value
                    draft.formdata = existing
                    draft.revision = uuid4()
            else:
                # no draft exists and no client revision, so create a draft
                draft = Draft(
                    table=Project.__tablename__,
                    table_row_id=obj.uuid,
                    formdata=incoming_data,
                    revision=uuid4(),
                )
            db.session.add(draft)
            db.session.commit()
            return {
                'status': 'ok',
                'revision': draft.revision,
                'form_nonce': form.form_nonce.default(),
            }
        return (
            {
                'status': 'error',
                'error': 'invalid_csrf',
                'error_description': _("Invalid CSRF token"),
            },
            400,
        )
