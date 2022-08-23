"""Mixins for model views."""
# TODO: Move each mixin into the main file for each view, or into <model>_mixin.py

from __future__ import annotations

from typing import Optional, Tuple, Type, Union
from uuid import uuid4

from flask import abort, g, request
from werkzeug.datastructures import MultiDict

from baseframe import _, forms
from coaster.auth import current_auth

from ..forms import SavedProjectForm
from ..models import (
    Draft,
    Profile,
    Project,
    ProjectRedirect,
    Session,
    TicketEvent,
    Venue,
    VenueRoom,
    db,
    sa,
)
from ..typing import ReturnRenderWith, ReturnView, UuidModelType
from .helpers import render_redirect


class ProfileCheckMixin:
    """Base class checks for suspended profiles."""

    profile: Optional[Profile] = None

    def after_loader(self) -> Optional[ReturnView]:
        """Post-process loader."""
        profile = self.profile
        if profile is None:
            raise ValueError("Subclass must set self.profile")
        g.profile = profile
        if not profile.is_active:
            abort(410)

        # mypy doesn't know this is a mixin, so it warns that `after_loader` is not
        # defined in the superclass. We ask it to ignore the problem here instead of
        # creating an elaborate workaround using `typing.TYPE_CHECKING`.
        # https://github.com/python/mypy/issues/5837
        return super().after_loader()  # type: ignore[misc]


class ProjectViewMixin(ProfileCheckMixin):
    model: Type[Project] = Project
    route_model_map = {'profile': 'profile.name', 'project': 'name'}
    obj: Project
    SavedProjectForm = SavedProjectForm
    CsrfForm = forms.Form

    def loader(self, profile, project, session=None) -> Union[Project, ProjectRedirect]:
        obj = (
            Project.query.join(Profile, Project.profile_id == Profile.id)
            .filter(
                Project.name == project,
                sa.func.lower(Profile.name) == sa.func.lower(profile),
            )
            .first()
        )
        if obj is None:
            obj_redirect = (
                ProjectRedirect.query.join(
                    Profile, ProjectRedirect.profile_id == Profile.id
                )
                .filter(
                    ProjectRedirect.name == project,
                    sa.func.lower(Profile.name) == sa.func.lower(profile),
                )
                .first_or_404()
            )
            return obj_redirect
        if obj.state.DELETED:
            abort(410)
        return obj

    def after_loader(self) -> Optional[ReturnView]:
        if isinstance(self.obj, ProjectRedirect):
            if self.obj.project:
                self.profile = self.obj.project.profile
                return render_redirect(
                    self.obj.project.url_for(),
                    302 if request.method == 'GET' else 303,
                )
            abort(410)  # Project has been deleted
        self.profile = self.obj.profile
        return super().after_loader()

    @property
    def project_currently_saved(self):
        return self.obj.is_saved_by(current_auth.user)


class ProfileViewMixin(ProfileCheckMixin):
    model = Profile
    route_model_map = {'profile': 'name'}
    obj: Profile
    SavedProjectForm = SavedProjectForm
    CsrfForm = forms.Form

    def loader(self, profile) -> Profile:
        profile = Profile.get(profile)
        if profile is None:
            abort(404)
        return profile

    def after_loader(self) -> Optional[ReturnView]:
        self.profile = self.obj
        return super().after_loader()


class SessionViewMixin(ProfileCheckMixin):
    model = Session
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'session': 'url_name_uuid_b58',
    }
    obj: Session
    SavedProjectForm = SavedProjectForm

    def loader(self, profile, project, session) -> Session:
        return (
            Session.query.join(Project, Profile)
            .filter(Session.url_name_uuid_b58 == session)
            .first_or_404()
        )

    def after_loader(self) -> Optional[ReturnView]:
        self.profile = self.obj.project.profile
        return super().after_loader()

    @property
    def project_currently_saved(self):
        return self.obj.project.is_saved_by(current_auth.user)


class VenueViewMixin(ProfileCheckMixin):
    model = Venue
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'venue': 'name',
    }
    obj: Venue

    def loader(self, profile, project, venue) -> Venue:
        return (
            Venue.query.join(Project, Profile)
            .filter(
                sa.func.lower(Profile.name) == sa.func.lower(profile),
                Project.name == project,
                Venue.name == venue,
            )
            .first_or_404()
        )

    def after_loader(self) -> Optional[ReturnView]:
        self.profile = self.obj.project.profile
        return super().after_loader()


class VenueRoomViewMixin(ProfileCheckMixin):
    model = VenueRoom
    route_model_map = {
        'profile': 'venue.project.profile.name',
        'project': 'venue.project.name',
        'venue': 'venue.name',
        'room': 'name',
    }
    obj: VenueRoom

    def loader(self, profile, project, venue, room) -> VenueRoom:
        return (
            VenueRoom.query.join(Venue, Project, Profile)
            .filter(
                sa.func.lower(Profile.name) == sa.func.lower(profile),
                Project.name == project,
                Venue.name == venue,
                VenueRoom.name == room,
            )
            .first_or_404()
        )

    def after_loader(self) -> Optional[ReturnView]:
        self.profile = self.obj.venue.project.profile
        return super().after_loader()


class TicketEventViewMixin(ProfileCheckMixin):
    model = TicketEvent
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'name': 'name',
    }
    obj: TicketEvent

    def loader(self, profile, project, name) -> TicketEvent:
        return (
            TicketEvent.query.join(Project, Profile)
            .filter(
                sa.func.lower(Profile.name) == sa.func.lower(profile),
                Project.name == project,
                TicketEvent.name == name,
            )
            .one_or_404()
        )

    def after_loader(self) -> Optional[ReturnView]:
        self.profile = self.obj.project.profile
        return super().after_loader()


class DraftViewMixin:
    obj: UuidModelType
    model: Type[UuidModelType]

    def get_draft(self, obj: Optional[UuidModelType] = None) -> Optional[Draft]:
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
        self, obj: Optional[UuidModelType] = None
    ) -> Union[Tuple[None, None], Tuple[int, dict]]:
        """
        Return a tuple of draft data.

        Contains the current draft revision and the formdata needed to initialize forms.
        """
        draft = self.get_draft(obj)
        if draft is not None:
            return draft.revision, draft.formdata
        return None, None

    def autosave_post(self, obj: Optional[UuidModelType] = None) -> ReturnRenderWith:
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
