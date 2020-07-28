from flask import flash, g, redirect

from baseframe import _, forms
from baseframe.forms import render_form
from coaster.auth import current_auth
from coaster.utils import make_name
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    render_with,
    requires_roles,
    route,
)

from .. import app, funnelapp
from ..forms import ProjectPostForm, SavedProjectForm
from ..models import Post, Profile, Project, db
from .decorators import legacy_redirect
from .login_session import requires_login
from .project import ProjectViewMixin


@Project.views('updates')
@route('/<profile>/<project>/updates')
class ProjectUpdatesView(ProjectViewMixin, UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('', methods=['GET'])
    @render_with('project_updates.html.jinja2', json=True)
    @requires_roles({'reader'})
    def updates(self):
        project_save_form = SavedProjectForm()
        return {
            'project': self.obj.current_access(),
            'new_update': self.obj.url_for('new_update'),
            'project_save_form': project_save_form,
            'csrf_form': forms.Form(),
        }

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def new_update(self):
        post_form = ProjectPostForm()
        post_form.form_nonce.data = post_form.form_nonce.default()

        if post_form.validate_on_submit():
            post = Post(user=current_auth.user, project=self.obj)
            post_form.populate_obj(post)
            post.name = make_name(post.title)
            db.session.add(post)
            db.session.commit()
            if post_form.restricted.data:
                post.make_restricted()
            db.session.commit()
            return redirect(post.url_for('project_view'), code=303)

        return render_form(
            form=post_form,
            title=_("Post an update"),
            submit=_("Save & preview"),
            cancel_url=self.obj.url_for('project_view'),
        )


@route('/<project>/updates', subdomain='<profile>')
class FunnelProjectUpdatesView(ProjectUpdatesView):
    pass


ProjectUpdatesView.init_app(app)
FunnelProjectUpdatesView.init_app(funnelapp)


@Post.features('publish')
def post_publishable(obj):
    return obj.state.DRAFT and 'editor' in obj.roles_for(current_auth.user)


@Post.views('project')
@route('/<profile>/<project>/updates/<post>')
class ProjectPostView(UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]
    model = Post
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'post': 'url_name_uuid_b58',
    }

    def loader(self, profile, project, post):
        post = (
            self.model.query.join(Project)
            .join(Profile, Project.profile_id == Profile.id)
            .filter(Post.url_name_uuid_b58 == post)
            .one_or_404()
        )

        g.profile = post.project.profile
        return post

    @route('', methods=['GET'])
    @render_with('project_update_details.html.jinja2')
    def project_view(self):
        return {
            'post': self.obj.current_access(),
            'publish_form': forms.Form(),
            'project': self.obj.project.current_access(),
        }

    @route('publish', methods=['POST'])
    @requires_roles({'editor'})
    def project_publish(self):
        if not self.obj.state.DRAFT:
            return redirect(self.obj.url_for('project_view'))
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
        return redirect(self.obj.project.url_for('updates'))

    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_roles({'editor'})
    def project_edit(self):
        post_form = ProjectPostForm(obj=self.obj)

        if post_form.validate_on_submit():
            post_form.populate_obj(self.obj)
            db.session.commit()
            flash(_("The update has been edited"), 'success')
            return redirect(self.obj.url_for('project_view'), code=303)

        return render_form(
            form=post_form,
            title=_("Edit update"),
            submit=_("Save"),
            cancel_url=self.obj.url_for('project_view'),
        )

    @route('delete', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_roles({'editor'})
    def project_delete(self):
        delete_form = forms.Form()

        if delete_form.validate_on_submit():
            self.obj.delete(actor=current_auth.user)
            db.session.commit()
            flash(_("The update has been deleted"), 'success')
            return redirect(self.obj.project.url_for('updates'))

        return render_form(
            form=delete_form,
            title=_("Delete update?"),
            message=_("Deletion is permanent and cannot be undone")
            if self.obj.state.UNPUBLISHED
            else _(
                "This update’s number (#{number}) will be skipped for the next update"
            ).format(number=self.obj.number),
            submit=_("Delete"),
            cancel_url=self.obj.url_for('project_view'),
        )


@route('/<project>/updates/<post>', subdomain='<profile>')
class FunnelProjectPostView(ProjectPostView):
    pass


ProjectPostView.init_app(app)
FunnelProjectPostView.init_app(funnelapp)
