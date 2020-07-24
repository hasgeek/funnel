from flask import flash, g, redirect

from baseframe import _, forms, request_is_xhr
from coaster.auth import current_auth
from coaster.utils import make_name
from coaster.views import ModelView, UrlForView, render_with, requires_roles, route

from .. import app
from ..forms import PostForm, SavedProjectForm
from ..models import Post, Profile, Project, db
from .decorators import legacy_redirect
from .helpers import requires_login
from .project import ProjectViewMixin


@Project.views('updates')
@route('/<profile>/<project>/updates')
class ProjectPostView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('', methods=['GET'])
    @render_with('project_posts.html.jinja2', json=True)
    @requires_login
    @requires_roles({'reader'})
    def posts(self):
        project_save_form = SavedProjectForm()

        if request_is_xhr():
            return {
                'posts': self.obj.views.json_posts(),
            }

        project_save_form = SavedProjectForm()
        return {
            'project': self.obj.current_access(),
            'new_post': self.obj.url_for('new_post'),
            'project_save_form': project_save_form,
            'csrf_form': forms.Form(),
        }

    @route('new', methods=['GET', 'POST'])
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
            return forms.render_redirect(post.url_for())

        post_form_html = forms.render_form(
            form=post_form,
            formid='post_form',
            title=_("Post update"),
            submit=_("Post"),
            ajax=True,
            with_chrome=False,
        )
        return {
            'posts': self.obj.views.json_posts(),
            'form': post_form_html,
        }


ProjectPostView.init_app(app)


@Post.views('main')
@route('/<profile>/<project>/posts/<url_name_uuid_b58>')
class ProjectPostDetailsView(UrlForView, ModelView):
    __decorators__ = [requires_login, legacy_redirect]
    model = Post
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'url_name_uuid_b58': 'url_name_uuid_b58',
    }

    def loader(self, profile, project, url_name_uuid_b58):
        post = (
            self.model.query.join(Profile, Project)
            .filter(
                Profile.name == profile,
                Project.name == project,
                Post.url_name_uuid_b58 == url_name_uuid_b58,
            )
            .first_or_404()
        )
        g.profile = post.project.profile
        return post

    @route('', methods=['GET'])
    @render_with('project_post.html.jinja2')
    @requires_roles({'reader'})
    def view(self):
        return {'post': self.obj.current_access()}

    @route('publish', methods=['POST'])
    @requires_roles({'editor'})
    def publish_draft(self):
        if not self.obj.state.DRAFT:
            return redirect(self.obj.url_for())
        form = forms.Form()
        if form.validate_on_submit():
            self.obj.publish(actor=current_auth.user)
            db.session.commit()
            flash(_("The update has been published"), 'success')
        else:
            flash(
                _(
                    "There was an error publishing this update. "
                    "Please refresh and try again"
                ),
                'error',
            )
        return redirect(self.obj.project.url_for('posts'))


ProjectPostDetailsView.init_app(app)
