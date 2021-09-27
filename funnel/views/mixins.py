from __future__ import annotations

from typing import Optional, Tuple, Type, Union
from uuid import uuid4

from flask import abort, g, redirect, request
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
    UuidMixin,
    Venue,
    VenueRoom,
    db,
)
from ..typing import ReturnRenderWith


class ProfileCheckMixin:
    """Base class checks for suspended profiles."""

    profile = None

    def after_loader(self):
        profile = self.profile
        if profile is None:
            raise ValueError("Subclass must set self.profile")
        g.profile = profile
        if not profile.is_active:
            abort(410)

        return super().after_loader()


class ProjectViewMixin(ProfileCheckMixin):
    model = Project
    route_model_map = {'profile': 'profile.name', 'project': 'name'}
    obj: Union[Project, ProjectRedirect]
    SavedProjectForm = SavedProjectForm
    CsrfForm = forms.Form

    def loader(self, profile, project, session=None):
        proj = (
            self.model.query.join(Profile)
            .filter(
                Project.name == project,
                db.func.lower(Profile.name) == db.func.lower(profile),
            )
            .first()
        )
        if proj is None:
            projredir = (
                ProjectRedirect.query.join(Profile)
                .filter(
                    ProjectRedirect.name == project,
                    db.func.lower(Profile.name) == db.func.lower(profile),
                )
                .first_or_404()
            )
            return projredir
        if proj.state.DELETED:
            abort(410)
        return proj

    def after_loader(self):
        if isinstance(self.obj, ProjectRedirect):
            if self.obj.project:
                self.profile = self.obj.project.profile
                return redirect(self.obj.project.url_for())
            else:
                abort(410)
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

    def loader(self, profile):
        profile = self.model.get(profile)
        if profile is None:
            abort(404)
        return profile

    def after_loader(self):
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

    def loader(self, profile, project, session):
        session = (
            self.model.query.join(Project, Profile)
            .filter(Session.url_name_uuid_b58 == session)
            .first_or_404()
        )
        return session

    def after_loader(self):
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

    def loader(self, profile, project, venue):
        venue = (
            self.model.query.join(Project, Profile)
            .filter(
                db.func.lower(Profile.name) == db.func.lower(profile),
                Project.name == project,
                Venue.name == venue,
            )
            .first_or_404()
        )
        return venue

    def after_loader(self):
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

    def loader(self, profile, project, venue, room):
        room = (
            self.model.query.join(Venue, Project, Profile)
            .filter(
                db.func.lower(Profile.name) == db.func.lower(profile),
                Project.name == project,
                Venue.name == venue,
                VenueRoom.name == room,
            )
            .first_or_404()
        )
        return room

    def after_loader(self):
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

    def loader(self, profile, project, name):
        return (
            self.model.query.join(Project, Profile)
            .filter(
                db.func.lower(Profile.name) == db.func.lower(profile),
                Project.name == project,
                TicketEvent.name == name,
            )
            .one_or_404()
        )

    def after_loader(self):
        self.profile = self.obj.project.profile
        return super().after_loader()


class DraftViewMixin:
    obj: UuidMixin
    model: Type[UuidMixin]

    def get_draft(self, obj: Optional[UuidMixin] = None) -> Optional[Draft]:
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
        self, obj: Optional[UuidMixin] = None
    ) -> Union[Tuple[None, None], Tuple[int, dict]]:
        """
        Return a tuple of draft data.

        Contains the current draft revision and the formdata needed to initialize forms.
        """
        draft = self.get_draft(obj)
        if draft is not None:
            return draft.revision, draft.formdata
        else:
            return None, None

    def autosave_post(self, obj: Optional[UuidMixin] = None) -> ReturnRenderWith:
        """Handle autosave POST requests."""
        obj = obj if obj is not None else self.obj
        if 'form.revision' not in request.form:
            # as form.autosave is true, the form should have `form.revision` field even if it's empty
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
                elif (
                    client_revision is not None
                    and str(draft.revision) == client_revision
                ):
                    # revision ID sent my client matches, save updated draft data and update revision ID
                    existing = draft.formdata
                    for key in incoming_data.keys():
                        if existing[key] != incoming_data[key]:
                            existing[key] = incoming_data[key]
                    draft.formdata = existing
                    draft.revision = uuid4()
            elif client_revision:  # Implicit: draft is None
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
            return {'revision': draft.revision, 'form_nonce': form.form_nonce.default()}
        else:
            return (
                {
                    'status': 'error',
                    'error': 'invalid_csrf',
                    'error_description': _("Invalid CSRF token"),
                },
                400,
            )
