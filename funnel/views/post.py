from flask import flash, g, redirect

from baseframe import _, forms
from baseframe.forms import render_form
from coaster.auth import current_auth
from coaster.utils import make_name
from coaster.views import ModelView, UrlForView, render_with, requires_roles, route

from .. import app
from ..forms import PostForm, SavedProjectForm
from ..models import Post, Profile, Project, db
from .decorators import legacy_redirect
from .helpers import requires_login
from .project import ProjectViewMixin


@Project.features('drafts')
def project_drafts(obj):
    return obj.current_roles.editor


@Project.views('json_posts')
def project_json_posts(obj):
    published_posts = []
    for post in obj.published_posts:
        if post.visibilisty_state.PUBLIC:
            published_posts.append(post)
        else:
            # Restricted posts
            if obj.current_roles.participant or obj.current_roles.crew:
                published_posts.append(post)
    return {
        'pinned': [post.current_access() for post in published_posts if post.is_pinned],
        'published': [post.current_access() for post in published_posts],
        'draft': (
            [post.current_access() for post in obj.draft_posts]
            if obj.current_roles.editor
            else []
        ),
    }


@Project.views('updates')
@route('/<profile>/<project>/updates')
class ProjectPostView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('', methods=['GET'])
    @render_with('project_posts.html.jinja2', json=True)
    @requires_roles({'reader'})
    def posts(self):
        project_save_form = SavedProjectForm()
        return {
            'posts': self.obj.views.json_posts(),
            'project': self.obj.current_access(),
            'new_post': self.obj.url_for('new_post'),
            'project_save_form': project_save_form,
            'csrf_form': forms.Form(),
        }

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def new_post(self):
        post_form = PostForm()
        post_form.form_nonce.data = post_form.form_nonce.default()

        if post_form.validate_on_submit():
            post = Post(user=current_auth.user, project=self.obj)
            post_form.populate_obj(post)
            post.name = make_name(post.title)
            if post_form.restricted.data:
                post.make_restricted()
            db.session.add(post)
            db.session.commit()
            return redirect(post.url_for(), code=303)

        return render_form(
            form=post_form,
            title=_("Post a update"),
            submit=_("Post"),
            cancel_url=self.obj.url_for(),
        )


ProjectPostView.init_app(app)


@Post.features('publish')
def post_publishable(obj):
    return obj.state.DRAFT and 'editor' in obj.roles_for(current_auth.user)


@Post.views('main')
@route('/<profile>/<project>/updates/<url_name_uuid_b58>')
class ProjectPostDetailsView(UrlForView, ModelView):
    __decorators__ = [legacy_redirect]
    model = Post
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'url_name_uuid_b58': 'url_name_uuid_b58',
    }

    def loader(self, profile, project, url_name_uuid_b58):
        project = (
            Project.query.join(Profile)
            .filter(Profile.name == profile, Project.name == project)
            .one_or_404()
        )

        post = (
            self.model.query.join(Project)
            .filter(
                Project.id == project.id, Post.url_name_uuid_b58 == url_name_uuid_b58,
            )
            .one_or_404()
        )

        g.profile = post.project.profile
        return post

    @route('', methods=['GET'])
    @render_with('project_post_details.html.jinja2')
    @requires_roles({'reader'})
    def view(self):
        project_save_form = SavedProjectForm()

        return {
            'post': self.obj.current_access(),
            'publish_form': forms.Form(),
            'project': self.obj.project.current_access(),
            'project_save_form': project_save_form,
            'csrf_form': forms.Form(),
        }

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

    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_roles({'editor'})
    def edit(self):
        post_form = PostForm(obj=self.obj)

        if post_form.validate_on_submit():
            post_form.populate_obj(self.obj)
            db.session.commit()
            flash(_("The update has been edited"), 'success')
            if self.obj.state.DRAFT:
                return redirect(self.obj.url_for())
            else:
                return redirect(self.obj.project.url_for('posts'))

        return render_form(
            form=post_form,
            title=_("Edit update"),
            submit=_("Save"),
            cancel_url=self.obj.url_for(),
        )

    @route('delete', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_roles({'editor'})
    def delete(self):
        delete_form = forms.Form()

        if delete_form.validate_on_submit():
            self.obj.delete(actor=current_auth.user)
            db.session.commit()
            flash(_("The update has been deleted"), 'success')
            return redirect(self.obj.project.url_for('posts'))

        return render_form(
            form=delete_form,
            title=_("Delete update"),
            message=_("Do you really wish to delete this post ‘{title}’? ").format(
                title=self.obj.title
            ),
            submit=_("Delete"),
            cancel_url=self.obj.url_for(),
        )


ProjectPostDetailsView.init_app(app)
