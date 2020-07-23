from flask import g, redirect

from baseframe import _, forms
from coaster.auth import current_auth
from coaster.utils import make_name
from coaster.views import ModelView, UrlForView, render_with, requires_roles, route

from .. import app
from ..forms import PostForm
from ..models import Post, Profile, Project, db
from .decorators import legacy_redirect
from .helpers import requires_login
from .project import ProjectViewMixin


@Project.views('posts')
@route('/<profile>/<project>/posts')
class ProjectPostView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('', methods=['GET'])
    @render_with('project_posts.html.jinja2', json=True)
    @requires_login
    @requires_roles({'reader'})
    def posts(self):
        post_form = PostForm()

        post_form_html = forms.render_form(
            form=post_form,
            action=self.obj.url_for('new_post'),
            formid='post_form',
            title=_("Post update"),
            submit=_("Post"),
            ajax=True,
            with_chrome=False,
        )

        return {
            'project': self.obj.current_access(),
            'post_form': post_form_html,
            'posts': self.obj.views.json_posts(),
        }

    @route('new', methods=['POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'editor'})
    def new_post(self):
        post_form = PostForm()

        if post_form.validate_on_submit():
            post = Post(user=current_auth.user, project=self.obj)
            post_form.populate_obj(post)
            post.name = make_name(post.title)
            post.publish(actor=current_auth.user)
            if post_form.restricted.data:
                post.make_restricted()
            db.session.add(post)
            db.session.commit()
            return redirect(self.obj.url_for('posts'))

        post_form_html = forms.render_form(
            form=post_form,
            formid='post_form',
            title=_("Post update"),
            submit=_("Post"),
            ajax=True,
            with_chrome=False,
        )
        return {
            'status': 'error',
            'post_form': post_form_html,
        }


ProjectPostView.init_app(app)


@Post.views('main')
@route('/<profile>/<project>/posts/<uuid_b58>')
class ProjectPostDetailsView(UrlForView, ModelView):
    __decorators__ = [requires_login, legacy_redirect]
    model = Post
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'uuid_b58': 'uuid_b58',
    }

    def loader(self, profile, project, uuid_b58):
        post = (
            self.model.query.join(Profile, Project)
            .filter(
                Profile.name == profile,
                Project.name == project,
                Post.uuid_b58 == uuid_b58,
            )
            .first_or_404()
        )
        g.profile = post.project.profile
        return post

    @route('', methods=['GET'])
    @render_with(json=True)
    @requires_roles({'reader'})
    def view(self):
        return {'post': self.obj.current_access()}


ProjectPostDetailsView.init_app(app)
