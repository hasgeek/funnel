from flask import abort, g, redirect, request
from coaster.utils import require_one_of
from ..models import (Project, Profile, ProjectRedirect, Proposal, ProposalRedirect, Session,
    UserGroup, Venue, VenueRoom, Section)


class ProjectViewMixin(object):
    model = Project
    route_model_map = {'profile': 'profile.name', 'project': 'name'}

    def loader(self, profile, project):
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
        g.profile = proposal.project.profile
        return proposal

    def after_loader(self):
        if isinstance(self.obj, ProposalRedirect):
            if self.obj.proposal:
                return redirect(self.obj.proposal.url_for())
            else:
                abort(410)
        super(ProposalViewMixin, self).after_loader()


class SessionViewMixin(object):
    model = Session
    route_model_map = {'profile': 'project.profile.name', 'project': 'project.name', 'session': 'url_name'}

    def loader(self, profile, project, session):
        session = self.model.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, Session.url_name == session
            ).first_or_404()
        g.profile = session.project.profile
        return session


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
