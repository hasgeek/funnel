"""Views for projects."""

from dataclasses import dataclass
from types import SimpleNamespace
import csv
import io

from flask import Response, abort, current_app, flash, render_template, request

from baseframe import _, __, forms
from baseframe.forms import render_delete_sqla, render_form, render_message
from coaster.auth import current_auth
from coaster.utils import getbool, make_name
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    get_next_url,
    render_with,
    requires_roles,
    route,
)

from .. import app
from ..forms import (
    CfpForm,
    ProjectBannerForm,
    ProjectBoxofficeForm,
    ProjectCfpTransitionForm,
    ProjectFeaturedForm,
    ProjectForm,
    ProjectLivestreamForm,
    ProjectNameForm,
    ProjectTransitionForm,
)
from ..models import (
    RSVP_STATUS,
    Profile,
    Project,
    RegistrationCancellationNotification,
    RegistrationConfirmationNotification,
    Rsvp,
    SavedProject,
    db,
)
from ..signals import project_role_change
from .helpers import html_in_json, render_redirect
from .jobs import import_tickets, tag_locations
from .login_session import (
    requires_login,
    requires_site_editor,
    requires_user_not_spammy,
)
from .mixins import DraftViewMixin, ProfileViewMixin, ProjectViewMixin
from .notification import dispatch_notification


@dataclass
class CountWords:
    """Labels for a count of registrations."""

    unregistered: str
    registered: str
    not_following: str
    following: str


registration_count_messages = [
    CountWords(__("Be the first to register!"), '', __("Be the first follower!"), ''),
    CountWords(
        __("One registration so far"),
        __("You have registered"),
        __("One follower so far"),
        __("You are following this"),
    ),
    CountWords(
        __("Two registrations so far"),
        __("You and one other have registered"),
        __("Two followers so far"),
        __("You and one other are following"),
    ),
    CountWords(
        __("Three registrations so far"),
        __("You and two others have registered"),
        __("Three followers so far"),
        __("You and two others are following"),
    ),
    CountWords(
        __("Four registrations so far"),
        __("You and three others have registered"),
        __("Four followers so far"),
        __("You and three others are following"),
    ),
    CountWords(
        __("Five registrations so far"),
        __("You and four others have registered"),
        __("Five followers so far"),
        __("You and four others are following"),
    ),
    CountWords(
        __("Six registrations so far"),
        __("You and five others have registered"),
        __("Six followers so far"),
        __("You and five others are following"),
    ),
    CountWords(
        __("Seven registrations so far"),
        __("You and six others have registered"),
        __("Seven followers so far"),
        __("You and six others are following"),
    ),
    CountWords(
        __("Eight registrations so far"),
        __("You and seven others have registered"),
        __("Eight followers so far"),
        __("You and seven others are following"),
    ),
    CountWords(
        __("Nine registrations so far"),
        __("You and eight others have registered"),
        __("Nine followers so far"),
        __("You and eight others are following"),
    ),
    CountWords(
        __("Ten registrations so far"),
        __("You and nine others have registered"),
        __("Ten followers so far"),
        __("You and nine others are following"),
    ),
]
greater_than_10_count = CountWords(
    __("{num} registrations so far"),
    __("You and {num} others have registered"),
    __("{num} followers so far"),
    __("You and {num} others are following"),
)


def get_registration_text(count: int, registered=False, follow_mode=False) -> str:
    if count <= 10:
        if registered and not follow_mode:
            return registration_count_messages[count].registered
        if not registered and not follow_mode:
            return registration_count_messages[count].unregistered
        if registered and follow_mode:
            return registration_count_messages[count].following
        return registration_count_messages[count].not_following
    if registered and not follow_mode:
        return greater_than_10_count.registered.format(num=count - 1)
    if not registered and not follow_mode:
        return greater_than_10_count.unregistered.format(num=count)
    if registered and follow_mode:
        return greater_than_10_count.following.format(num=count - 1)
    return greater_than_10_count.not_following.format(num=count)


@Project.features('rsvp')
def feature_project_rsvp(obj: Project) -> bool:
    return (
        obj.state.PUBLISHED
        and (
            obj.boxoffice_data is None
            or 'item_collection_id' not in obj.boxoffice_data
            or not obj.boxoffice_data['item_collection_id']
        )
        and (obj.start_at is None or not obj.state.PAST)
    )


@Project.features('tickets')
def feature_project_tickets(obj: Project) -> bool:
    return (
        obj.start_at is not None
        and obj.boxoffice_data is not None
        and 'item_collection_id' in obj.boxoffice_data
        and obj.boxoffice_data['item_collection_id']
        and not obj.state.PAST
    )


@Project.features('tickets_or_rsvp')
def feature_project_tickets_or_rsvp(obj: Project) -> bool:
    return obj.features.tickets() or obj.features.rsvp()


@Project.features('rsvp_unregistered')
def feature_project_register(obj: Project) -> bool:
    rsvp = obj.rsvp_for(current_auth.user)
    return rsvp is None or not rsvp.state.YES


@Project.features('rsvp_registered')
def feature_project_deregister(obj: Project) -> bool:
    rsvp = obj.rsvp_for(current_auth.user)
    return rsvp is not None and rsvp.state.YES


@Project.features('schedule_no_sessions')
def feature_project_has_no_sessions(obj: Project) -> bool:
    return obj.state.PUBLISHED and not obj.start_at


@Project.features('comment_new')
def feature_project_comment_new(obj: Project) -> bool:
    return obj.current_roles.participant


@Project.features('post_update')
def feature_project_post_update(obj: Project) -> bool:
    return obj.current_roles.editor


@Project.features('follow_mode')
def project_follow_mode(obj: Project) -> bool:
    return obj.start_at is None


@Project.views('registration_text')
def project_registration_text(obj: Project) -> str:
    return get_registration_text(
        count=obj.rsvp_count_going,
        registered=obj.features.rsvp_registered(),
        follow_mode=obj.features.follow_mode(),
    )


@Project.views('register_button_text')
def project_register_button_text(obj: Project) -> str:
    if obj.features.follow_mode():
        return _("Follow")
    return _("Register")


@Profile.views('project_new')
@route('/<profile>')
class ProfileProjectView(ProfileViewMixin, UrlForView, ModelView):
    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'admin'})
    @requires_user_not_spammy()
    def new_project(self):
        form = ProjectForm(model=Project, profile=self.obj)

        if request.method == 'GET':
            form.timezone.data = current_app.config.get('TIMEZONE')
        if form.validate_on_submit():
            project = Project(user=current_auth.user, profile=self.obj)
            form.populate_obj(project)
            project.make_name()
            db.session.add(project)
            db.session.commit()

            flash(_("Your new project has been created"), 'info')

            # tag locations
            tag_locations.queue(project.id)

            return render_redirect(project.url_for())
        return render_form(
            form=form,
            title=_("Create a new project"),
            submit=_("Create project"),
            cancel_url=self.obj.url_for(),
        )


ProfileProjectView.init_app(app)


# mypy has trouble with the definition of `obj` and `model` between ProjectViewMixin and
# DraftViewMixin
@Project.views('main')
@route('/<profile>/<project>/')
class ProjectView(  # type: ignore[misc]
    ProjectViewMixin, DraftViewMixin, UrlChangeCheck, UrlForView, ModelView
):
    @route('')
    @render_with(html_in_json('project.html.jinja2'))
    @requires_roles({'reader'})
    def view(self):
        return {
            'project': self.obj.current_access(datasets=('primary', 'related')),
            'featured_proposals': [
                _p.current_access(datasets=('without_parent', 'related'))
                for _p in self.obj.proposals.filter_by(featured=True)
            ],
        }

    @route('sub')
    @route('proposals')
    @render_with(html_in_json('project_submissions.html.jinja2'))
    @requires_roles({'reader'})
    def view_proposals(self):
        return {
            'project': self.obj.current_access(datasets=('primary', 'related')),
            'submissions': [
                _p.current_access(datasets=('without_parent', 'related'))
                for _p in self.obj.proposals
            ],
        }

    @route('videos')
    @render_with(html_in_json('project_videos.html.jinja2'))
    def session_videos(self):
        return {
            'project': self.obj.current_access(datasets=('primary', 'related')),
        }

    @route('editslug', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def edit_slug(self):
        form = ProjectNameForm(obj=self.obj)
        form.name.prefix = self.obj.profile.url_for(_external=True)
        # Hasgeek profile URLs currently do not have a trailing slash, but this form
        # should not depend on this being guaranteed. Add a trailing slash if one is
        # required.
        if not form.name.prefix.endswith('/'):
            form.name.prefix += '/'
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            return render_redirect(self.obj.url_for())
        return render_form(form=form, title=_("Customize the URL"), submit=_("Save"))

    @route('editlivestream', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def edit_livestream(self):
        form = ProjectLivestreamForm(obj=self.obj)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            return render_redirect(self.obj.url_for())
        return render_form(
            form=form, title=_("Add or edit livestream URLs"), submit=_("Save changes")
        )

    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'editor'})
    def edit(self):
        if request.method == 'GET':
            # Find draft if it exists
            draft_revision, initial_formdata = self.get_draft_data()

            # Initialize forms with draft initial formdata.
            # If no draft exists, initial_formdata is None.
            # WTForms will ignore formdata if it's None.
            form = ProjectForm(
                obj=self.obj,
                profile=self.obj.profile,
                model=Project,
                formdata=initial_formdata,
            )

            if not self.obj.timezone:
                form.timezone.data = str(current_auth.user.timezone)

            return render_form(
                form=form,
                title=_("Edit project"),
                submit=_("Save changes"),
                autosave=True,
                draft_revision=draft_revision,
            )
        if getbool(request.args.get('form.autosave')):
            return self.autosave_post()
        form = ProjectForm(obj=self.obj, profile=self.obj.profile, model=Project)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            tag_locations.queue(self.obj.id)

            # Find and delete draft if it exists
            if self.get_draft() is not None:
                self.delete_draft()
                db.session.commit()

            return render_redirect(self.obj.url_for())
        # Reset nonce to avoid conflict with autosave
        form.form_nonce.data = form.form_nonce.default()
        return render_form(
            form=form,
            title=_("Edit project"),
            submit=_("Save changes"),
            autosave=True,
            draft_revision=request.form.get('form.revision'),
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'profile_admin'})
    def delete(self):
        """Delete project if safe to do so."""
        if not self.obj.is_safe_to_delete():
            return render_message(
                title=_("This project has submissions"),
                message=_(
                    "Submissions must be deleted or transferred before the project"
                    " can be deleted"
                ),
            )
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Delete project ‘{title}’? This will delete everything in the project."
                " This operation is permanent and cannot be undone"
            ).format(title=self.obj.title),
            success=_(
                "You have deleted project ‘{title}’ and all its associated content"
            ).format(title=self.obj.title),
            next=self.obj.profile.url_for(),
            cancel_url=self.obj.url_for(),
        )

    @route('update_banner', methods=['GET', 'POST'])
    @render_with('update_logo_modal.html.jinja2')
    @requires_roles({'editor'})
    def update_banner(self):
        form = ProjectBannerForm(obj=self.obj, profile=self.obj.profile)
        edit_logo_url = self.obj.url_for('edit_banner')
        delete_logo_url = self.obj.url_for('remove_banner')
        return {
            'edit_logo_url': edit_logo_url,
            'delete_logo_url': delete_logo_url,
            'form': form,
        }

    @route('edit_banner', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def edit_banner(self):
        form = ProjectBannerForm(obj=self.obj, profile=self.obj.profile)
        if request.method == 'POST':
            if form.validate_on_submit():
                form.populate_obj(self.obj)
                db.session.commit()
                flash(_("Your changes have been saved"), 'info')
                return render_redirect(self.obj.url_for())
            return render_form(form=form, title="", submit=_("Save banner"), ajax=True)
        return render_form(
            form=form,
            title="",
            submit=_("Save banner"),
            ajax=True,
            template='img_upload_formlayout.html.jinja2',
        )

    @route('remove_banner', methods=['POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'editor'})
    def remove_banner(self):
        form = self.CsrfForm()
        if form.validate_on_submit():
            self.obj.bg_image = None
            db.session.commit()
            return render_redirect(self.obj.url_for())
        current_app.logger.error(
            "CSRF form validation error when removing project banner"
        )
        flash(
            _("Were you trying to remove the banner? Try again to confirm"),
            'error',
        )
        return render_redirect(self.obj.url_for())

    @route('cfp', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def cfp(self):
        form = CfpForm(obj=self.obj, model=Project)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            if self.obj.cfp_end_at and not self.obj.cfp_start_at:
                self.obj.cfp_start_at = db.func.utcnow()
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return render_redirect(self.obj.url_for('view_proposals'))
        return render_template(
            'project_cfp.html.jinja2', form=form, ref_id='form-cfp', project=self.obj
        )

    @route('boxoffice_data', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'promoter'})
    def edit_boxoffice_data(self):
        boxoffice_data = self.obj.boxoffice_data or {}
        form = ProjectBoxofficeForm(
            obj=SimpleNamespace(
                org=boxoffice_data.get('org', ''),
                item_collection_id=boxoffice_data.get('item_collection_id', ''),
            ),
            model=Project,
        )
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            self.obj.boxoffice_data['org'] = form.org.data
            self.obj.boxoffice_data['item_collection_id'] = form.item_collection_id.data
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return render_redirect(self.obj.url_for())
        return render_form(
            form=form,
            formid='boxoffice',
            title=_("Edit ticket client details"),
            submit=_("Save changes"),
        )

    @route('transition', methods=['POST'])
    @requires_login
    @requires_roles({'editor'})
    def transition(self):
        transition_form = ProjectTransitionForm(obj=self.obj)
        if (
            transition_form.validate_on_submit()
        ):  # check if the provided transition is valid
            transition = getattr(
                self.obj.current_access(), transition_form.transition.data
            )
            transition()  # call the transition
            db.session.commit()
            flash(transition.data['message'], 'success')
        else:
            flash(_("Invalid transition for this project"), 'error')
            abort(403)
        return render_redirect(self.obj.url_for())

    @route('cfp_transition', methods=['POST'])
    @requires_login
    @requires_roles({'editor'})
    def cfp_transition(self):
        cfp_transition = ProjectCfpTransitionForm(obj=self.obj)
        if cfp_transition.validate_on_submit():
            cfp_transition.populate_obj(self.obj)
            db.session.commit()
            if self.obj.cfp_state.OPEN:
                return {
                    'status': 'ok',
                    'message': _("This project can now receive submissions"),
                }
            return {
                'status': 'ok',
                'message': _("This project will no longer accept submissions"),
            }
        return {
            'status': 'error',
            'error': 'validation',
            'error_description': _("Invalid form submission"),
        }

    @route('register', methods=['POST'])
    @requires_login
    def register(self):
        form = forms.Form()
        if form.validate_on_submit():
            rsvp = Rsvp.get_for(self.obj, current_auth.user, create=True)
            if not rsvp.state.YES:
                rsvp.rsvp_yes()
                db.session.commit()
                project_role_change.send(
                    self.obj, actor=current_auth.user, user=current_auth.user
                )
                db.session.commit()
                dispatch_notification(
                    RegistrationConfirmationNotification(document=rsvp)
                )
        else:
            flash(_("Were you trying to register? Try again to confirm"), 'error')
        return render_redirect(get_next_url(referrer=request.referrer))

    @route('deregister', methods=['POST'])
    @requires_login
    def deregister(self):
        form = forms.Form()
        if form.validate_on_submit():
            rsvp = Rsvp.get_for(self.obj, current_auth.user)
            if rsvp is not None and not rsvp.state.NO:
                rsvp.rsvp_no()
                db.session.commit()
                project_role_change.send(
                    self.obj, actor=current_auth.user, user=current_auth.user
                )
                db.session.commit()
                dispatch_notification(
                    RegistrationCancellationNotification(document=rsvp)
                )
        else:
            flash(
                _("Were you trying to cancel your registration? Try again to confirm"),
                'error',
            )
        return render_redirect(get_next_url(referrer=request.referrer))

    @route('rsvp_list')
    @render_with('project_rsvp_list.html.jinja2')
    @requires_login
    @requires_roles({'promoter'})
    def rsvp_list(self):
        return {
            'project': self.obj.current_access(datasets=('primary', 'related')),
            'going_rsvps': [
                _r.current_access(datasets=('without_parent', 'related', 'related'))
                for _r in self.obj.rsvps_with(RSVP_STATUS.YES)
            ],
        }

    def get_rsvp_state_csv(self, state):
        outfile = io.StringIO(newline='')
        out = csv.writer(outfile)
        out.writerow(['fullname', 'email', 'created_at'])
        for rsvp in self.obj.rsvps_with(state):
            out.writerow(
                [
                    rsvp.user.fullname,
                    rsvp.user.default_email(context=rsvp.project.profile) or '',
                    rsvp.created_at.astimezone(self.obj.timezone)
                    .replace(second=0, microsecond=0, tzinfo=None)
                    .isoformat(),  # Strip precision from timestamp
                ]
            )

        outfile.seek(0)
        return Response(
            outfile.getvalue(),
            content_type='text/csv',
            headers=[
                (
                    'Content-Disposition',
                    f'attachment;filename='
                    f'"ticket-participants-{make_name(self.obj.title)}-{state}.csv"',
                )
            ],
        )

    @route('rsvp_list/yes.csv')
    @requires_login
    @requires_roles({'promoter'})
    def rsvp_list_yes_csv(self):
        """Return a CSV of RSVP participants who answered Yes."""
        return self.get_rsvp_state_csv(state=RSVP_STATUS.YES)

    @route('rsvp_list/maybe.csv')
    @requires_login
    @requires_roles({'promoter'})
    def rsvp_list_maybe_csv(self):
        """Return a CSV of RSVP participants who answered Maybe."""
        return self.get_rsvp_state_csv(state=RSVP_STATUS.MAYBE)

    @route('save', methods=['POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'reader'})
    def save(self):
        form = self.SavedProjectForm()
        form.form_nonce.data = form.form_nonce.default()
        if form.validate_on_submit():
            proj_save = SavedProject.query.filter_by(
                user=current_auth.user, project=self.obj
            ).first()
            if form.save.data:
                if proj_save is None:
                    proj_save = SavedProject(user=current_auth.user, project=self.obj)
                    form.populate_obj(proj_save)
                    db.session.commit()
            else:
                if proj_save is not None:
                    db.session.delete(proj_save)
                    db.session.commit()
            # Send new form nonce
            return {'status': 'ok', 'form_nonce': form.form_nonce.data}
        return (
            {
                'status': 'error',
                'error': 'project_save_form_invalid',
                'error_description': _("This page timed out. Reload and try again"),
                'form_nonce': form.form_nonce.data,
            },
            400,
        )

    @route('admin', methods=['GET', 'POST'])
    @render_with('project_admin.html.jinja2')
    @requires_login
    @requires_roles({'promoter', 'usher'})
    def admin(self):
        """Render admin panel for at-venue promoter operations."""
        csrf_form = forms.Form()
        if csrf_form.validate_on_submit():
            if request.form.get('form.id') == 'sync-tickets':
                for ticket_client in self.obj.ticket_clients:
                    if ticket_client and ticket_client.name.lower() in [
                        'explara',
                        'boxoffice',
                    ]:
                        import_tickets.queue(ticket_client.id)
                flash(
                    _(
                        "Importing tickets from vendors…"
                        " Reload the page in about 30 seconds…"
                    ),
                    'info',
                )
            return render_redirect(self.obj.url_for('admin'))
        return {
            'profile': self.obj.profile.current_access(datasets=('primary',)),
            'project': self.obj.current_access(datasets=('without_parent', 'related')),
            'ticket_events': [_e.current_access() for _e in self.obj.ticket_events],
            'ticket_clients': [_c.current_access() for _c in self.obj.ticket_clients],
            'ticket_types': [_t.current_access() for _t in self.obj.ticket_types],
        }

    @route('settings', methods=['GET', 'POST'])
    @render_with('project_settings.html.jinja2')
    @requires_login
    @requires_roles({'editor', 'promoter', 'usher'})
    def settings(self):
        transition_form = ProjectTransitionForm(obj=self.obj)
        return {
            'project': self.obj.current_access(datasets=('primary', 'related')),
            'transition_form': transition_form,
        }

    @route('comments', methods=['GET'])
    @render_with(html_in_json('project_comments.html.jinja2'))
    @requires_roles({'reader'})
    def comments(self):
        project = self.obj.current_access(datasets=('primary', 'related'))
        comments = self.obj.commentset.views.json_comments()
        subscribed = bool(self.obj.commentset.current_roles.document_subscriber)
        new_comment_url = self.obj.commentset.url_for('new')
        comments_url = self.obj.commentset.url_for()
        last_seen_url = (
            self.obj.commentset.url_for('update_last_seen_at') if subscribed else None
        )
        return {
            'project': project,
            'subscribed': subscribed,
            'comments': comments,
            'new_comment_url': new_comment_url,
            'comments_url': comments_url,
            'last_seen_url': last_seen_url,
        }

    @route('update_featured', methods=['POST'])
    @requires_site_editor
    def update_featured(self):
        featured_form = ProjectFeaturedForm(obj=self.obj)
        if featured_form.validate_on_submit():
            featured_form.populate_obj(self.obj)
            db.session.commit()
            if self.obj.site_featured:
                return {'status': 'ok', 'message': 'This project has been featured.'}
            return {
                'status': 'ok',
                'message': 'This project is no longer featured.',
            }
        return render_redirect(get_next_url(referrer=True))


ProjectView.init_app(app)
