import csv
import io

from flask import (
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
)

from baseframe import _, forms
from baseframe.forms import render_form
from coaster.auth import current_auth
from coaster.utils import getbool, make_name
from coaster.views import (
    ModelView,
    UrlForView,
    jsonp,
    render_with,
    requires_roles,
    route,
)

from .. import app, funnelapp
from ..forms import (
    CfpForm,
    CommentDeleteForm,
    CommentForm,
    ProjectBoxofficeForm,
    ProjectCfpTransitionForm,
    ProjectForm,
    ProjectLivestreamForm,
    ProjectNameForm,
    ProjectScheduleTransitionForm,
    ProjectTransitionForm,
    RsvpTransitionForm,
    SavedProjectForm,
)
from ..jobs import import_tickets, tag_locations
from ..models import (
    RSVP_STATUS,
    Comment,
    Profile,
    Project,
    Proposal,
    Rsvp,
    SavedProject,
    Voteset,
    db,
)
from .decorators import legacy_redirect
from .helpers import requires_login
from .mixins import DraftViewMixin, ProfileViewMixin, ProjectViewMixin
from .proposal import proposal_data, proposal_data_flat, proposal_headers
from .schedule import schedule_data
from .venue import room_data, venue_data


def project_data(project):
    return {
        'id': project.id,
        'name': project.name,
        'title': project.title,
        'datelocation': project.datelocation,
        'timezone': project.timezone.zone,
        'start_at': (
            project.schedule_start_at.astimezone(project.timezone).date().isoformat()
            if project.schedule_start_at
            else None
        ),
        'end_at': (
            project.schedule_end_at.astimezone(project.timezone).date().isoformat()
            if project.schedule_end_at
            else None
        ),
        'status': project.state.value,
        'state': project.state.label.name,
        'url': project.url_for(_external=True),
        'website': project.website.url if project.website is not None else "",
        'json_url': project.url_for('json', _external=True),
        'bg_image': project.bg_image.url if project.bg_image is not None else "",
        'calendar_weeks_full': project.calendar_weeks_full,
        'calendar_weeks_compact': project.calendar_weeks_compact,
        'registration_header_text': project.registration_header_text._asdict(),
    }


@Project.features('rsvp')
def feature_project_rsvp(obj):
    return (
        obj.schedule_state.PUBLISHED
        and (
            obj.boxoffice_data is None
            or 'item_collection_id' not in obj.boxoffice_data
            or not obj.boxoffice_data['item_collection_id']
        )
        and not obj.schedule_state.PAST
    )


@Project.features('tickets')
def feature_project_tickets(obj):
    return (
        obj.schedule_state.PUBLISHED
        and obj.boxoffice_data is not None
        and 'item_collection_id' in obj.boxoffice_data
        and obj.boxoffice_data['item_collection_id']
        and not obj.schedule_state.PAST
    )


@Project.features('tickets_or_rsvp')
def feature_project_tickets_or_rsvp(obj):
    return obj.features.tickets() or obj.features.rsvp()


@Project.features('rsvp_register')
def feature_project_register(obj):
    rsvp = obj.rsvp_for(current_auth.user)
    return rsvp is None or not rsvp.state.YES


@Project.features('rsvp_deregister')
def feature_project_deregister(obj):
    rsvp = obj.rsvp_for(current_auth.user)
    return rsvp is not None and rsvp.state.YES


@Project.features('schedule_no_sessions')
def feature_project_has_no_sessions(obj):
    return obj.schedule_state.PUBLISHED and not obj.schedule_start_at


@Project.features('comment_new')
def feature_project_comment_new(obj):
    return obj.current_roles.participant is True


@Project.features('registration')
def feature_project_registration(obj):
    return obj.rsvp_for(current_auth.user) is None


@Project.features('deregistration')
def feature_project_deregistration(obj):
    return obj.rsvp_for(current_auth.user) is not None


@Profile.views('project_new')
@route('/<profile>')
class ProfileProjectView(ProfileViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'admin'})
    def new_project(self):
        form = ProjectForm(model=Project, parent=self.obj)

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


@route('/', subdomain='<profile>')
class FunnelProfileProjectView(ProfileProjectView):
    pass


ProfileProjectView.init_app(app)
FunnelProfileProjectView.init_app(funnelapp)


@Project.views('main')
@route('/<profile>/<project>/')
class ProjectView(ProjectViewMixin, DraftViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('project.html.jinja2')
    @requires_roles({'reader'})
    def view(self):
        transition_form = ProjectTransitionForm(obj=self.obj)
        schedule_transition_form = ProjectScheduleTransitionForm(obj=self.obj)
        project_save_form = SavedProjectForm()
        rsvp_form = RsvpTransitionForm()
        current_rsvp = self.obj.rsvp_for(current_auth.user)
        return {
            'project': self.obj,
            'current_rsvp': current_rsvp,
            'empty_form': forms.Form(),
            'rsvp_form': rsvp_form,
            'transition_form': transition_form,
            'schedule_transition_form': schedule_transition_form,
            'project_save_form': project_save_form,
        }

    @route('proposals')
    @render_with('proposals.html.jinja2')
    @requires_roles({'reader'})
    def view_proposals(self):
        cfp_transition_form = ProjectCfpTransitionForm(obj=self.obj)
        project_save_form = SavedProjectForm()
        return {
            'project': self.obj,
            'cfp_transition_form': cfp_transition_form,
            'project_save_form': project_save_form,
            'empty_form': forms.Form(),
        }

    @route('videos')
    @render_with('session_videos.html.jinja2')
    def session_videos(self):
        cfp_transition_form = ProjectCfpTransitionForm(obj=self.obj)
        project_save_form = SavedProjectForm()
        return {
            'project': self.obj,
            'cfp_transition_form': cfp_transition_form,
            'project_save_form': project_save_form,
            'empty_form': forms.Form(),
        }

    @route('json')
    @render_with(json=True)
    @requires_roles({'reader'})
    def json(self):
        proposals = (
            Proposal.query.filter_by(project=self.obj)
            .order_by(db.desc('created_at'))
            .all()
        )
        return jsonp(
            **{
                'project': project_data(self.obj),
                'venues': [venue_data(venue) for venue in self.obj.venues],
                'rooms': [room_data(room) for room in self.obj.rooms],
                'proposals': [proposal_data(proposal) for proposal in proposals],
                'schedule': schedule_data(self.obj),
            }
        )

    @route('csv')
    @requires_roles({'reader'})
    def csv(self):
        proposals = (
            Proposal.query.filter_by(project=self.obj)
            .order_by(db.desc('created_at'))
            .all()
        )
        outfile = io.StringIO()
        out = csv.writer(outfile)
        out.writerow(proposal_headers + ['status'])
        for proposal in proposals:
            out.writerow(proposal_data_flat(proposal))
        outfile.seek(0)
        return Response(
            outfile.getvalue(),
            content_type='text/csv',
            headers=[
                (
                    'Content-Disposition',
                    'attachment;filename="{profile}-{project}.csv"'.format(
                        profile=self.obj.profile.name, project=self.obj.name
                    ),
                )
            ],
        )

    @route('editslug', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def edit_slug(self):
        form = ProjectNameForm(obj=self.obj)
        # Profile URLs:
        # HasGeek: https://hasgeek.com/rootconf (no /)
        # Talkfunnel: https://rootconf.talkfunnel.com/ (has /)
        form.name.prefix = self.obj.profile.url_for(_external=True)
        if not form.name.prefix.endswith('/'):
            form.name.prefix += '/'
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            return redirect(self.obj.url_for())
        return render_form(
            form=form, title=_("Customize the URL"), submit=_("Save changes")
        )

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
                parent=self.obj.profile,
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
        elif request.method == 'POST':
            if getbool(request.args.get('form.autosave')):
                return self.autosave_post()
            else:
                form = ProjectForm(obj=self.obj, parent=self.obj.profile, model=Project)
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
    @requires_roles({'concierge'})
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
            flash(_("Invalid transition for this project's CfP"), 'error')
            abort(403)
        return redirect(self.obj.url_for('view_proposals'))

    @route('schedule_transition', methods=['POST'])
    @requires_login
    @requires_roles({'editor'})
    def schedule_transition(self):
        schedule_transition_form = ProjectScheduleTransitionForm(obj=self.obj)
        if (
            schedule_transition_form.validate_on_submit()
        ):  # check if the provided transition is valid
            transition = getattr(
                self.obj.current_access(),
                schedule_transition_form.schedule_transition.data,
            )
            transition()  # call the transition
            db.session.commit()
            flash(transition.data['message'], 'success')
        else:
            flash(_("Invalid transition for this project's schedule"), 'error')
            abort(403)
        return redirect(self.obj.url_for())

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
                rsvp.rsvp_yes()
                db.session.commit()
                flash(
                    _("You have successfully registered for '%s'" % self.obj.title),
                    'success',
                )
        else:
            flash(_("There was a problem registering. Please try again"), 'error')
        return redirect(self.obj.url_for(), code=303)

    @route('deregister', methods=['POST'])
    @requires_login
    def deregister(self):
        form = forms.Form()
        if form.validate_on_submit():
            rsvp = Rsvp.get_for(self.obj, current_auth.user)
            if rsvp is not None and not rsvp.state.NO:
                rsvp.rsvp_no()
                db.session.commit()
                flash(
                    _("Your registration has been cancelled for '%s'" % self.obj.title),
                    'success',
                )
        else:
            flash(
                _("There was a problem cancelling your registration. Please try again"),
                'error',
            )
        return redirect(self.obj.url_for(), code=303)

    @route('rsvp_list')
    @render_with('project_rsvp_list.html.jinja2')
    @requires_login
    @requires_roles({'concierge'})
    def rsvp_list(self):
        return {'project': self.obj, 'statuses': RSVP_STATUS}

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
                        filename='participants-{project}-{state}'.format(
                            project=make_name(self.obj.title), state=state
                        )
                    ),
                )
            ],
        )

    @route('rsvp_list/yes.csv')
    @requires_login
    @requires_roles({'concierge'})
    def rsvp_list_yes_csv(self):
        """
        Returns a CSV of given contacts
        """
        return self.get_rsvp_state_csv(state=RSVP_STATUS.YES)

    @route('rsvp_list/maybe.csv')
    @requires_login
    @requires_roles({'concierge'})
    def rsvp_list_maybe_csv(self):
        """
        Returns a CSV of given contacts
        """
        return self.get_rsvp_state_csv(state=RSVP_STATUS.MAYBE)

    @route('save', methods=['POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'reader'})
    def save(self):
        form = SavedProjectForm()
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
                    'error_description': _(
                        "Something went wrong, please reload and try again"
                    ),
                    'form_nonce': form.form_nonce.data,
                },
                400,
            )
        return redirect(self.obj.url_for(), code=303)

    @route('admin', methods=['GET', 'POST'])
    @render_with('admin.html.jinja2')
    @requires_login
    @requires_roles({'concierge', 'usher'})
    def admin(self):
        csrf_form = forms.Form()
        if csrf_form.validate_on_submit():
            for ticket_client in self.obj.ticket_clients:
                if ticket_client and ticket_client.name.lower() in [
                    'explara',
                    'boxoffice',
                ]:
                    import_tickets.queue(ticket_client.id)
            flash(
                _(
                    "Importing tickets from vendors...Refresh the page in about 30 seconds..."
                ),
                'info',
            )
            return redirect(self.obj.url_for('admin'), code=303)
        return {
            'profile': self.obj.profile,
            'project': self.obj,
            'events': self.obj.events,
            'csrf_form': csrf_form,
            'empty_form': forms.Form(),
        }

    @route('settings', methods=['GET', 'POST'])
    @render_with('settings.html.jinja2')
    @requires_login
    @requires_roles({'editor', 'concierge', 'usher'})
    def settings(self):
        transition_form = ProjectTransitionForm(obj=self.obj)
        schedule_transition_form = ProjectScheduleTransitionForm(obj=self.obj)
        cfp_transition_form = ProjectCfpTransitionForm(obj=self.obj)
        project_save_form = SavedProjectForm()
        return {
            'project': self.obj,
            'transition_form': transition_form,
            'cfp_transition_form': cfp_transition_form,
            'schedule_transition_form': schedule_transition_form,
            'project_save_form': project_save_form,
            'empty_form': forms.Form(),
        }

    @route('comments', methods=['GET'])
    @render_with('project_comments.html.jinja2')
    @requires_roles({'reader'})
    def comments(self):
        project_save_form = SavedProjectForm()
        comments = (
            Comment.query.join(Voteset)
            .filter(
                Comment.commentset == self.obj.commentset, Comment.parent_id.is_(None)
            )
            .order_by(Voteset.count, Comment.created_at.asc())
            .all()
        )
        commentform = CommentForm(model=Comment)
        delcommentform = CommentDeleteForm()
        return {
            'project': self.obj,
            'project_save_form': project_save_form,
            'comments': comments,
            'commentform': commentform,
            'delcommentform': delcommentform,
            'empty_form': forms.Form(),
        }


@route('/<project>/', subdomain='<profile>')
class FunnelProjectView(ProjectView):
    pass


ProjectView.init_app(app)
FunnelProjectView.init_app(funnelapp)
