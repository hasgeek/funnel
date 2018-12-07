from flask import g
from coaster.views import UrlForView, ModelView
from ..models import Project, Profile, ProjectRedirect


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
