from uuid import uuid4
from flask import abort, g, redirect, request
from baseframe import _, forms
from coaster.utils import require_one_of
from werkzeug.datastructures import MultiDict
from ..models import (Draft, Project, Profile, ProjectRedirect, Proposal, ProposalRedirect, Session,
    UserGroup, Venue, VenueRoom, Section, db)


class ProjectViewMixin(object):
    model = Project
    route_model_map = {'profile': 'profile.name', 'project': 'name'}

    def loader(self, profile, project, session=None):
        proj = self.model.query.join(Profile).filter(
                Project.name == project, Profile.name == profile
            ).first()
        if proj is None:
            projredir = ProjectRedirect.query.join(Profile).filter(
                    ProjectRedirect.name == project, Profile.name == profile
                ).first_or_404()
            proj = projredir.project
        g.profile = proj.profile
        return proj


class ProfileViewMixin(object):
    model = Profile
    route_model_map = {'profile': 'name'}

    def loader(self, profile):
        profile = self.model.query.filter(Profile.name == profile).first_or_404()
        g.profile = profile
        return profile


class ProposalViewMixin(object):
    model = Proposal
    route_model_map = {
        'profile': 'project.profile.name', 'project': 'project.name',
        'url_name_suuid': 'url_name_suuid', 'url_id_name': 'url_id_name'}

    def loader(self, profile, project, url_name_suuid=None, url_id_name=None):
        require_one_of(url_name_suuid=url_name_suuid, url_id_name=url_id_name)
        if url_name_suuid:
            proposal = self.model.query.join(Project, Profile).filter(
                    Proposal.url_name_suuid == url_name_suuid
                ).first_or_404()
        else:
            proposal = self.model.query.join(Project, Profile).filter(
                    Profile.name == profile, Project.name == project, Proposal.url_name == url_id_name
                ).first()
            if proposal is None:
                if request.method == 'GET':
                    redirect = ProposalRedirect.query.join(Project, Profile).filter(
                        Profile.name == profile, Project.name == project, ProposalRedirect.url_name == url_id_name
                        ).first_or_404()
                    return redirect
                else:
                    abort(404)
        return proposal

    def after_loader(self):
        if isinstance(self.obj, ProposalRedirect):
            if self.obj.proposal:
                g.profile = self.obj.proposal.project.profile
                return redirect(self.obj.proposal.url_for())
            else:
                abort(410)
        g.profile = self.obj.project.profile
        super(ProposalViewMixin, self).after_loader()


class SessionViewMixin(object):
    model = Session
    route_model_map = {'profile': 'project.profile.name', 'project': 'project.name', 'session': 'url_name_suuid'}

    def loader(self, profile, project, session):
        session = self.model.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, Session.url_name_suuid == session
            ).first_or_404()
        return session

    def after_loader(self):
        g.profile = self.obj.project.profile
        super(SessionViewMixin, self).after_loader()


class UserGroupViewMixin(object):
    model = UserGroup
    route_model_map = {'profile': 'project.profile.name', 'project': 'project.name', 'group': 'name'}

    def loader(self, profile, project, group):
        group = self.model.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, UserGroup.name == group
            ).first_or_404()
        g.profile = group.project.profile
        return group


class VenueViewMixin(object):
    model = Venue
    route_model_map = {'profile': 'project.profile.name', 'project': 'project.name', 'venue': 'name'}

    def loader(self, profile, project, venue):
        venue = self.model.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, Venue.name == venue
            ).first_or_404()
        g.profile = venue.project.profile
        return venue


class VenueRoomViewMixin(object):
    model = VenueRoom
    route_model_map = {'profile': 'venue.project.profile.name', 'project': 'venue.project.name', 'venue': 'venue.name', 'room': 'name'}

    def loader(self, profile, project, venue, room):
        room = self.model.query.join(Venue, Project, Profile).filter(
                Profile.name == profile, Project.name == project, Venue.name == venue, VenueRoom.name == room
            ).first_or_404()
        g.profile = room.venue.project.profile
        return room


class SectionViewMixin(object):
    model = Section
    route_model_map = {'profile': 'project.profile.name', 'project': 'project.name', 'section': 'name'}

    def loader(self, profile, project, section):
        section = self.model.query.join(Project).join(Profile).filter(
            Project.name == project, Profile.name == profile,
            Section.name == section
            ).first_or_404()
        g.profile = section.project.profile
        return section


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
            return {'status': 'error', 'error_identifier': 'form_missing_revision_field', 'error_description': _("Form must contain a revision ID.")}, 400

        # CSRF check
        if forms.Form().validate_on_submit():
            incoming_data = MultiDict(request.form.items(multi=True))
            client_revision = incoming_data.pop('form.revision')
            incoming_data.pop('csrf_token', None)

            # find the last draft
            draft = self.get_draft(obj)

            if draft is not None:
                if client_revision is None or (client_revision is not None and str(draft.revision) != client_revision):
                    # draft exists, but the form did not send a revision ID,
                    # OR revision ID sent by client does not match the last revision ID
                    return {'status': 'error', 'error_identifier': 'missing_or_invalid_revision', 'error_description': _("There have been changes to this draft since you last edited it. Please reload.")}, 400
                elif client_revision is not None and str(draft.revision) == client_revision:
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
                return {'status': 'error', 'error_identifier': 'invalid_or_expired_revision', 'error_description': _("Invalid revision ID or the existing changes have been submitted already. Please reload.")}, 400
            else:
                # no draft exists, create one
                draft = Draft(
                    table=Project.__tablename__, table_row_id=obj.uuid,
                    formdata=incoming_data, revision=uuid4()
                    )
            db.session.add(draft)
            db.session.commit()
            return {'revision': draft.revision}
        else:
            return {'status': 'error', 'error_identifier': 'invalid_csrf', 'error_description': _("Invalid CSRF token")}, 400
