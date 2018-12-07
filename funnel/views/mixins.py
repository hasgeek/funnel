from flask import g, abort, redirect
from ..models import (Project, Profile, ProjectRedirect, Proposal, ProposalRedirect, Session,
    Comment, Commentset, UserGroup, Venue, VenueRoom)


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
    route_model_map = {'profile': 'project.profile.name', 'project': 'project.name', 'proposal': 'url_name'}

    def loader(self, profile, project, proposal):
        proposal = self.model.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, Proposal.url_name == proposal
            ).first_or_404()
        g.profile = proposal.project.profile
        return proposal


class SessionViewMixin(object):
    model = Session
    route_model_map = {'profile': 'project.profile.name', 'project': 'project.name', 'session': 'url_name'}

    def loader(self, profile, project, session):
        session = self.model.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, Session.url_name == session
            ).first_or_404()
        g.profile = session.project.profile
        return session


class CommentViewMixin(object):
    model = Comment
    route_model_map = {'comment': 'id'}

    def loader(self, profile, project, proposal, comment):
        comment = self.model.query.filter(Comment.id == comment).first_or_404()
        self.proposal = Proposal.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, Proposal.url_name == proposal
            ).first_or_404()
        g.profile = self.proposal.project.profile
        return comment


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
