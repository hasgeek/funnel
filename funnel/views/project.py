from collections import namedtuple
import csv
import io

from flask import (
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
)

from baseframe import _, forms, request_is_xhr
from baseframe.forms import (
    render_delete_sqla,
    render_form,
    render_message,
    render_redirect,
)
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
    CommentForm,
    ProjectBannerForm,
    ProjectBoxofficeForm,
    ProjectCfpTransitionForm,
    ProjectForm,
    ProjectLivestreamForm,
    ProjectNameForm,
    ProjectTransitionForm,
    RsvpTransitionForm,
)
from ..models import (
    RSVP_STATUS,
    Comment,
    Profile,
    Project,
    RegistrationCancellationNotification,
    RegistrationConfirmationNotification,
    Rsvp,
    SavedProject,
    db,
)
from .jobs import import_tickets, tag_locations
from .login_session import requires_login
from .mixins import DraftViewMixin, ProfileViewMixin, ProjectViewMixin
from .notification import dispatch_notification

CountWords = namedtuple(
    'CountWords', ['unregistered', 'registered', 'not_following', 'following']
)

registration_count_messages = [
    CountWords(_("Be the first to register!"), None, _("Be the first follower!"), None),
    CountWords(
        _("One registration so far"),
        _("You have registered"),
        _("One follower so far"),
        _("You are following this"),
    ),
    CountWords(
        _("Two registrations so far"),
        _("You and one other have registered"),
        _("Two followers so far"),
        _("You and one other are following"),
    ),
    CountWords(
        _("Three registrations so far"),
        _("You and two others have registered"),
        _("Three followers so far"),
        _("You and two others are following"),
    ),
    CountWords(
        _("Four registrations so far"),
        _("You and three others have registered"),
        _("Four followers so far"),
        _("You and three others are following"),
    ),
    CountWords(
        _("Five registrations so far"),
        _("You and four others have registered"),
        _("Five followers so far"),
        _("You and four others are following"),
    ),
    CountWords(
        _("Six registrations so far"),
        _("You and five others have registered"),
        _("Six followers so far"),
        _("You and five others are following"),
    ),
    CountWords(
        _("Seven registrations so far"),
        _("You and six others have registered"),
        _("Seven followers so far"),
        _("You and six others are following"),
    ),
    CountWords(
        _("Eight registrations so far"),
        _("You and seven others have registered"),
        _("Eight followers so far"),
        _("You and seven others are following"),
    ),
    CountWords(
        _("Nine registrations so far"),
        _("You and eight others have registered"),
        _("Nine followers so far"),
        _("You and eight others are following"),
    ),
    CountWords(
        _("Ten registrations so far"),
        _("You and nine others have registered"),
        _("Ten followers so far"),
        _("You and nine others are following"),
    ),
]


def get_registration_text(count, registered=False, follow_mode=False):
    if count <= 10:
        if registered and not follow_mode:
            return registration_count_messages[count].registered
        elif not registered and not follow_mode:
            return registration_count_messages[count].unregistered
        elif registered and follow_mode:
            return registration_count_messages[count].following
        return registration_count_messages[count].not_following
    if registered and not follow_mode:
        return _("You and {num} others have registered").format(num=count - 1)
    elif registered and not follow_mode:
        return _("{num} registrations so far").format(num=count)
    elif registered and follow_mode:
        return _("You and {num} others are following").format(num=count - 1)
    return _("{num} followers so far").format(num=count)


@Project.features('rsvp')
def feature_project_rsvp(obj):
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
def feature_project_tickets(obj):
    return (
        obj.start_at is not None
        and obj.boxoffice_data is not None
        and 'item_collection_id' in obj.boxoffice_data
        and obj.boxoffice_data['item_collection_id']
        and not obj.state.PAST
    )


@Project.features('tickets_or_rsvp')
def feature_project_tickets_or_rsvp(obj):
    return obj.features.tickets() or obj.features.rsvp()


@Project.features('rsvp_unregistered')
def feature_project_register(obj):
    rsvp = obj.rsvp_for(current_auth.user)
    return rsvp is None or not rsvp.state.YES


@Project.features('rsvp_registered')
def feature_project_deregister(obj):
    rsvp = obj.rsvp_for(current_auth.user)
    return rsvp is not None and rsvp.state.YES


@Project.features('schedule_no_sessions')
def feature_project_has_no_sessions(obj):
    return obj.state.PUBLISHED and not obj.start_at


@Project.features('comment_new')
def feature_project_comment_new(obj):
    return obj.current_roles.participant


@Project.features('post_update')
def feature_project_post_update(obj):
    return obj.current_roles.editor


@Project.features('follow_mode')
def project_follow_mode(obj):
    return obj.start_at is None


@Project.views('registration_text')
def project_registration_text(obj):
    return get_registration_text(
        count=obj.rsvp_count_going,
        registered=obj.features.rsvp_registered(),
        follow_mode=obj.features.follow_mode(),
    )


@Profile.views('project_new')
@route('/<profile>')
class ProfileProjectView(ProfileViewMixin, UrlForView, ModelView):
    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'admin'})
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

            return redirect(project.url_for(), code=303)
        return render_form(
            form=form,
            title=_("Create a new project"),
            submit=_("Create project"),
            cancel_url=self.obj.url_for(),
        )


ProfileProjectView.init_app(app)


@Project.views('main')
@route('/<profile>/<project>/')
class ProjectView(
    ProjectViewMixin, DraftViewMixin, UrlChangeCheck, UrlForView, ModelView
):
    @route('')
    @render_with('project.html.jinja2')
    @requires_roles({'reader'})
    def view(self):
        transition_form = ProjectTransitionForm(obj=self.obj)
        rsvp_form = RsvpTransitionForm()
        current_rsvp = self.obj.rsvp_for(current_auth.user)
        featured_proposals = self.obj.proposals.filter_by(featured=True)
        return {
            'project': self.obj.current_access(),
            'current_rsvp': current_rsvp,
            'rsvp_form': rsvp_form,
            'transition_form': transition_form,
            'featured_proposals': featured_proposals,
        }

    @route('sub')
    @route('proposals')
    @render_with('project_submissions.html.jinja2')
    @requires_roles({'reader'})
    def view_proposals(self):
        cfp_transition_form = ProjectCfpTransitionForm(obj=self.obj)
        return {
            'project': self.obj,
            'cfp_transition_form': cfp_transition_form,
        }

    @route('videos')
    @render_with('project_videos.html.jinja2')
    def session_videos(self):
        return {
            'project': self.obj,
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
            return redirect(self.obj.url_for())
        return render_form(form=form, title=_("Customize the URL"), submit=_("Save"))

    @route('editlivestream', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def edit_livestream(self):
        form = ProjectLivestreamForm(obj=self.obj)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            return redirect(self.obj.url_for())
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

            # Don't allow user to directly manipulate timestamps when it's done via
            # Session objects
            if self.obj.schedule_start_at:
                del form.start_at
                del form.end_at

            if not self.obj.timezone:
                form.timezone.data = str(current_auth.user.timezone)

            return render_form(
                form=form,
                title=_("Edit project"),
                submit=_("Save changes"),
                autosave=True,
                draft_revision=draft_revision,
            )
        elif request.method == 'POST':
            if getbool(request.args.get('form.autosave')):
                return self.autosave_post()
            else:
                form = ProjectForm(
                    obj=self.obj, profile=self.obj.profile, model=Project
                )
                if form.validate_on_submit():
                    form.populate_obj(self.obj)
                    db.session.commit()
                    flash(_("Your changes have been saved"), 'info')
                    tag_locations.queue(self.obj.id)

                    # Find and delete draft if it exists
                    if self.get_draft() is not None:
                        self.delete_draft()
                        db.session.commit()

                    return redirect(self.obj.url_for(), code=303)
                else:
                    # Reset nonce to avoid conflict with autosave
                    form.form_nonce.data = form.form_nonce.default()
                    return render_form(
                        form=form,
                        title=_("Edit project"),
                        submit=_("Save changes"),
                        autosave=True,
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
                return render_redirect(self.obj.url_for(), code=303)
            else:
                return render_form(
                    form=form, title="", submit=_("Save banner"), ajax=True
                )
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
            return render_redirect(self.obj.url_for(), code=303)
        else:
            current_app.logger.error(
                "CSRF form validation error when removing project banner"
            )
            flash(
                _("Were you trying to remove the banner? Try again to confirm"),
                'error',
            )
            return render_redirect(self.obj.url_for(), code=303)

    @route('cfp', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def cfp(self):
        form = CfpForm(obj=self.obj, model=Project)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.url_for('view_proposals'), code=303)
        return render_template('project_cfp.html.jinja2', form=form, project=self.obj)

    @route('boxoffice_data', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'promoter'})
    def edit_boxoffice_data(self):
        form = ProjectBoxofficeForm(obj=self.obj, model=Project)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.url_for(), code=303)
        return render_form(
            form=form, title=_("Edit ticket client details"), submit=_("Save changes")
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
        return redirect(self.obj.url_for())

    @route('cfp_transition', methods=['POST'])
    @requires_login
    @requires_roles({'editor'})
    def cfp_transition(self):
        cfp_transition_form = ProjectCfpTransitionForm(obj=self.obj)
        if (
            cfp_transition_form.validate_on_submit()
        ):  # check if the provided transition is valid
            transition = getattr(
                self.obj.current_access(), cfp_transition_form.cfp_transition.data
            )
            transition()  # call the transition
            db.session.commit()
            flash(transition.data['message'], 'success')
        else:
            flash(_("Invalid transition for this project’s CfP"), 'error')
            abort(403)
        return redirect(self.obj.url_for('view_proposals'))

    @route('rsvp', methods=['POST'])
    @requires_login
    @requires_roles({'reader'})
    def rsvp_transition(self):
        form = RsvpTransitionForm()
        if form.validate_on_submit():
            rsvp = Rsvp.get_for(self.obj, current_auth.user, create=True)
            transition = getattr(rsvp, form.transition.data)
            transition()
            db.session.commit()
            flash(transition.data['message'], 'success')
        else:
            flash(_("This response is not valid"), 'error')
        return redirect(self.obj.url_for(), code=303)

    @route('register', methods=['POST'])
    @requires_login
    def register(self):
        form = forms.Form()
        if form.validate_on_submit():
            rsvp = Rsvp.get_for(self.obj, current_auth.user, create=True)
            if not rsvp.state.YES:
                rsvp.rsvp_yes(subscribe_comments=True)
                db.session.commit()
                dispatch_notification(
                    RegistrationConfirmationNotification(document=rsvp)
                )
        else:
            flash(_("Were you trying to register? Try again to confirm"), 'error')
        return redirect(get_next_url(referrer=request.referrer), code=303)

    @route('deregister', methods=['POST'])
    @requires_login
    def deregister(self):
        form = forms.Form()
        if form.validate_on_submit():
            rsvp = Rsvp.get_for(self.obj, current_auth.user)
            if rsvp is not None and not rsvp.state.NO:
                rsvp.rsvp_no()
                db.session.commit()
                dispatch_notification(
                    RegistrationCancellationNotification(document=rsvp)
                )
        else:
            flash(
                _("Were you trying to cancel your registration? Try again to confirm"),
                'error',
            )
        return redirect(get_next_url(referrer=request.referrer), code=303)

    @route('rsvp_list')
    @render_with('project_rsvp_list.html.jinja2')
    @requires_login
    @requires_roles({'promoter'})
    def rsvp_list(self):
        return {
            'project': self.obj,
            'going_rsvps': self.obj.rsvps_with(RSVP_STATUS.YES),
        }

    def get_rsvp_state_csv(self, state):
        outfile = io.StringIO()
        out = csv.writer(outfile)
        out.writerow(['fullname', 'email', 'created_at'])
        for rsvp in self.obj.rsvps_with(state):
            out.writerow(
                [
                    rsvp.user.fullname,
                    (
                        rsvp.user.email
                        if rsvp.user.email
                        else rsvp.user.emailclaims[0]
                        if rsvp.user.emailclaims
                        else ''
                    ),
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
                    'attachment;filename="{filename}.csv"'.format(
                        filename='ticket-participants-{project}-{state}'.format(
                            project=make_name(self.obj.title), state=state
                        )
                    ),
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
        else:
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
            return redirect(self.obj.url_for('admin'), code=303)
        return {
            'profile': self.obj.profile,
            'project': self.obj,
            'ticket_events': self.obj.ticket_events,
        }

    @route('settings', methods=['GET', 'POST'])
    @render_with('project_settings.html.jinja2')
    @requires_login
    @requires_roles({'editor', 'promoter', 'usher'})
    def settings(self):
        transition_form = ProjectTransitionForm(obj=self.obj)
        cfp_transition_form = ProjectCfpTransitionForm(obj=self.obj)
        return {
            'project': self.obj,
            'transition_form': transition_form,
            'cfp_transition_form': cfp_transition_form,
        }

    @route('comments', methods=['GET'])
    @render_with('project_comments.html.jinja2')
    @requires_roles({'reader'})
    def comments(self):
        comments = self.obj.commentset.views.json_comments()
        subscribed = bool(self.obj.commentset.current_roles.document_subscriber)
        if request_is_xhr():
            return jsonify(
                {
                    'subscribed': subscribed,
                    'comments': comments,
                }
            )
        else:
            commentform = CommentForm(model=Comment)
            return {
                'project': self.obj,
                'subscribed': subscribed,
                'comments': comments,
                'commentform': commentform,
                'delcommentform': forms.Form(),
            }

    @route('update_featured', methods=['POST'])
    def update_featured(self):
        if not current_auth.user.is_site_editor:
            return abort(403)
        featured_form = self.obj.forms.featured()
        if featured_form.validate_on_submit():
            featured_form.populate_obj(self.obj)
            db.session.commit()
            if self.obj.site_featured:
                return {'status': 'ok', 'message': 'This project has been featured.'}
            else:
                return {
                    'status': 'ok',
                    'message': 'This project is no longer featured.',
                }
        return redirect(get_next_url(referrer=True), 303)


ProjectView.init_app(app)
