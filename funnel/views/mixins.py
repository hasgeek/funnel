# -*- coding: utf-8 -*-

from uuid import uuid4

from flask import abort, g, redirect, request
from werkzeug.datastructures import MultiDict

from baseframe import _, forms
from coaster.auth import current_auth
from coaster.utils import require_one_of

from ..models import (
    Draft,
    Event,
    Profile,
    Project,
    ProjectRedirect,
    Proposal,
    ProposalRedirect,
    ProposalSuuidRedirect,
    Session,
    Venue,
    VenueRoom,
    db,
)


class ProjectViewMixin(object):
    model = Project
    route_model_map = {'profile': 'profile.name', 'project': 'name'}

    def loader(self, profile, project, session=None):
        proj = (
            self.model.query.join(Profile)
            .filter(Project.name == project, Profile.name == profile)
            .first()
        )
        if proj is None:
            projredir = (
                ProjectRedirect.query.join(Profile)
                .filter(ProjectRedirect.name == project, Profile.name == profile)
                .first_or_404()
            )
            return projredir
        if proj.state.DELETED:
            abort(410)
        return proj

    def after_loader(self):
        if isinstance(self.obj, ProjectRedirect):
            if self.obj.project:
                g.profile = self.obj.project.profile
                return redirect(self.obj.project.url_for())
            else:
                abort(410)
        g.profile = self.obj.profile
        return super(ProjectViewMixin, self).after_loader()

    @property
    def project_currently_saved(self):
        return self.obj.is_saved_by(current_auth.user)


class ProfileViewMixin(object):
    model = Profile
    route_model_map = {'profile': 'name'}

    def loader(self, profile):
        profile = self.model.get(profile)
        if not profile:
            abort(404)
        g.profile = profile
        return profile


class ProposalViewMixin(object):
    model = Proposal
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'url_name_uuid_b58': 'url_name_uuid_b58',
        'url_id_name': 'url_id_name',
    }

    def loader(self, profile, project, url_name_uuid_b58=None, url_id_name=None):
        require_one_of(url_name_uuid_b58=url_name_uuid_b58, url_id_name=url_id_name)
        if url_name_uuid_b58:
            proposal = (
                self.model.query.join(Project, Profile)
                .filter(Proposal.url_name_uuid_b58 == url_name_uuid_b58)
                .first()
            )
            if proposal is None:
                if request.method == 'GET':
                    redirect = (
                        ProposalSuuidRedirect.query.join(Proposal)
                        .filter(
                            ProposalSuuidRedirect.suuid
                            == url_name_uuid_b58.split('-')[-1]
                        )
                        .first_or_404()
                    )
                    return redirect
                else:
                    abort(404)
        else:
            proposal = (
                self.model.query.join(Project, Profile)
                .filter(
                    Profile.name == profile,
                    Project.name == project,
                    Proposal.url_name == url_id_name,
                )
                .first()
            )
            if proposal is None:
                if request.method == 'GET':
                    redirect = (
                        ProposalRedirect.query.join(Project, Profile)
                        .filter(
                            Profile.name == profile,
                            Project.name == project,
                            ProposalRedirect.url_name == url_id_name,
                        )
                        .first_or_404()
                    )
                    return redirect
                else:
                    abort(404)
        if proposal.project.state.DELETED or proposal.state.DELETED:
            abort(410)
        return proposal

    def after_loader(self):
        if isinstance(self.obj, (ProposalRedirect, ProposalSuuidRedirect)):
            if self.obj.proposal:
                g.profile = self.obj.proposal.project.profile
                return redirect(self.obj.proposal.url_for())
            else:
                abort(410)
        g.profile = self.obj.project.profile
        return super(ProposalViewMixin, self).after_loader()


class SessionViewMixin(object):
    model = Session
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'session': 'url_name_uuid_b58',
    }

    def loader(self, profile, project, session):
        session = (
            self.model.query.join(Project, Profile)
            .filter(
                Profile.name == profile,
                Project.name == project,
                Session.url_name_uuid_b58 == session,
            )
            .first_or_404()
        )
        return session

    def after_loader(self):
        g.profile = self.obj.project.profile
        return super(SessionViewMixin, self).after_loader()

    @property
    def project_currently_saved(self):
        return self.obj.project.is_saved_by(current_auth.user)


class VenueViewMixin(object):
    model = Venue
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'venue': 'name',
    }

    def loader(self, profile, project, venue):
        venue = (
            self.model.query.join(Project, Profile)
            .filter(
                Profile.name == profile, Project.name == project, Venue.name == venue
            )
            .first_or_404()
        )
        g.profile = venue.project.profile
        return venue


class VenueRoomViewMixin(object):
    model = VenueRoom
    route_model_map = {
        'profile': 'venue.project.profile.name',
        'project': 'venue.project.name',
        'venue': 'venue.name',
        'room': 'name',
    }

    def loader(self, profile, project, venue, room):
        room = (
            self.model.query.join(Venue, Project, Profile)
            .filter(
                Profile.name == profile,
                Project.name == project,
                Venue.name == venue,
                VenueRoom.name == room,
            )
            .first_or_404()
        )
        g.profile = room.venue.project.profile
        return room


class EventViewMixin(object):
    model = Event
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'name': 'name',
    }

    def loader(self, profile, project, name):
        event = (
            self.model.query.join(Project, Profile)
            .filter(
                Profile.name == profile, Project.name == project, Event.name == name
            )
            .one_or_404()
        )
        return event

    def after_loader(self):
        g.profile = self.obj.project.profile
        return super(EventViewMixin, self).after_loader()


class DraftViewMixin(object):
    def get_draft(self, obj=None):
        """
        Returns the draft object for `obj`. Defaults to `self.obj`.
        `obj` is needed in case of multi-model views.
        """
        obj = obj if obj is not None else self.obj
        return Draft.query.get((self.model.__tablename__, obj.uuid))

    def delete_draft(self, obj=None):
        """
        Deletes draft for `obj`, or `self.obj` if `obj` is `None`.
        """
        draft = self.get_draft(obj)
        if draft is not None:
            db.session.delete(draft)
        else:
            raise ValueError(_("There is no draft for the given object."))

    def get_draft_data(self, obj=None):
        """
        Returns a tuple of the current draft revision and the formdata needed to initialize forms
        """
        draft = self.get_draft(obj)
        if draft is not None:
            return draft.revision, draft.formdata
        else:
            return None, None

    def autosave_post(self, obj=None):
        """
        Handles autosave POST requests
        """
        obj = obj if obj is not None else self.obj
        if 'form.revision' not in request.form:
            # as form.autosave is true, the form should have `form.revision` field even if it's empty
            return (
                {
                    'status': 'error',
                    'error': 'form_missing_revision_field',
                    'error_description': _("Form must contain a revision ID."),
                },
                400,
            )

        # CSRF check
        form = forms.Form()
        if form.validate_on_submit():
            incoming_data = MultiDict(request.form.items(multi=True))
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
                                "There have been changes to this draft since you last edited it. Please reload."
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
            elif draft is None and client_revision:
                # The form contains a revision ID but no draft exists.
                # Somebody is making autosave requests with an invalid draft ID.
                return (
                    {
                        'status': 'error',
                        'error': 'invalid_or_expired_revision',
                        'error_description': _(
                            "Invalid revision ID or the existing changes have been submitted already. Please reload."
                        ),
                    },
                    400,
                )
            else:
                # no draft exists, create one
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
