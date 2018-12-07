from flask import g, abort, redirect
from coaster.views import UrlForView, ModelView
from ..models import Project, Profile, ProjectRedirect, Proposal, ProposalRedirect, Session, Comment, Commentset


class ProjectViewBaseMixin(UrlForView, ModelView):
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


class ProfileViewBaseMixin(UrlForView, ModelView):
    model = Profile
    route_model_map = {'profile': 'name'}

    def loader(self, profile):
        profile = self.model.query.filter(Profile.name == profile).first_or_404()
        g.profile = profile
        return profile


class ProposalViewBaseMixin(UrlForView, ModelView):
    model = Proposal
    route_model_map = {'profile': 'project.profile.name', 'project': 'project.name', 'proposal': 'url_name'}

    def loader(self, profile, project, proposal):
        proposal = self.model.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, Proposal.url_name == proposal
            ).first_or_404()
        g.profile = proposal.project.profile
        return proposal


class SessionViewBaseMixin(UrlForView, ModelView):
    model = Session
    route_model_map = {'profile': 'project.profile.name', 'project': 'project.name', 'session': 'url_name'}

    def loader(self, profile, project, session):
        session = self.model.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, Session.url_name == session
            ).first_or_404()
        g.profile = session.project.profile
        return session


class CommentViewBaseMixin(UrlForView, ModelView):
    model = Comment
    route_model_map = {
        'comment': 'id'
        }

    def loader(self, profile, project, proposal, comment):
        comment = self.model.query.filter(Comment.id == comment).first_or_404()
        self.proposal = Proposal.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, Proposal.url_name == proposal
            ).first_or_404()
        g.profile = self.proposal.project.profile
        return comment
