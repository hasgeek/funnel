from coaster.views import UrlForView, ModelView
from .project import Project
from .profile import Profile


class ProjectViewBaseMixin(UrlForView, ModelView):
    model = Project
    route_model_map = {'profile': 'profile.name', 'project': 'name'}

    def loader(self, profile, project):
        return self.model.query.join(Profile).filter(
                Project.name == project, Profile.name == profile
            ).first_or_404()
