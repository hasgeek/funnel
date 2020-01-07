# -*- coding: utf-8 -*-

import six

from flask import (
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
)

import unicodecsv

from baseframe import _, forms
from baseframe.forms import render_form
from coaster.auth import current_auth
from coaster.utils import getbool
from coaster.views import (
    ModelView,
    UrlForView,
    jsonp,
    render_with,
    requires_permission,
    route,
)

from .. import app, funnelapp, lastuser
from ..forms import (
    CfpForm,
    ProjectBoxofficeForm,
    ProjectCfpTransitionForm,
    ProjectForm,
    ProjectScheduleTransitionForm,
    ProjectTransitionForm,
    RsvpTransitionForm,
    SavedProjectForm,
)
from ..jobs import import_tickets, tag_locations
from ..models import RSVP_STATUS, Project, Proposal, Rsvp, SavedProject, db
from .decorators import legacy_redirect
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
        'bg_color': project.bg_color,
        'explore_url': (
            project.explore_url.url if project.explore_url is not None else ""
        ),
        'calendar_weeks': project.calendar_weeks,
    }


@route('/<profile>')
class ProfileProjectView(ProfileViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new_project')
    def new_project(self):
        form = ProjectForm(model=Project, parent=self.obj)
        if request.method == 'GET':
            form.timezone.data = current_app.config.get('TIMEZONE')
        if form.validate_on_submit():
            project = Project(user=current_auth.user, profile=self.obj)
            form.populate_obj(project)
            db.session.add(project)
            db.session.commit()
            flash(_("Your new project has been created"), 'info')
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


@route('/<profile>/<project>/')
class ProjectView(ProjectViewMixin, DraftViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('project.html.jinja2')
    @requires_permission('view')
    def view(self):
        transition_form = ProjectTransitionForm(obj=self.obj)
        schedule_transition_form = ProjectScheduleTransitionForm(obj=self.obj)
        project_save_form = SavedProjectForm()
        rsvp_form = RsvpTransitionForm()
        current_rsvp = self.obj.rsvp_for(current_auth.user)
        return {
            'project': self.obj,
            'current_rsvp': current_rsvp,
            'rsvp_form': rsvp_form,
            'transition_form': transition_form,
            'schedule_transition_form': schedule_transition_form,
            'project_save_form': project_save_form,
        }

    @route('proposals')
    @render_with('proposals.html.jinja2')
    @requires_permission('view')
    def view_proposals(self):
        cfp_transition_form = ProjectCfpTransitionForm(obj=self.obj)
        project_save_form = SavedProjectForm()
        return {
            'project': self.obj,
            'cfp_transition_form': cfp_transition_form,
            'project_save_form': project_save_form,
        }

    @route('json')
    @render_with(json=True)
    @requires_permission('view')
    def json(self):
        proposals = (
            Proposal.query.filter_by(project=self.obj)
            .order_by(db.desc('created_at'))
            .all()
        )
        return jsonp(
            **{
                'project': project_data(self.obj),
                'space': project_data(
                    self.obj
                ),  # TODO: Remove when the native app switches over
                'venues': [venue_data(venue) for venue in self.obj.venues],
                'rooms': [room_data(room) for room in self.obj.rooms],
                'proposals': [proposal_data(proposal) for proposal in proposals],
                'schedule': schedule_data(self.obj),
            }
        )

    @route('csv')
    @requires_permission('view')
    def csv(self):
        proposals = (
            Proposal.query.filter_by(project=self.obj)
            .order_by(db.desc('created_at'))
            .all()
        )
        outfile = six.BytesIO()
        out = unicodecsv.writer(outfile, encoding='utf-8')
        out.writerow(proposal_headers + ['status'])
        for proposal in proposals:
            out.writerow(proposal_data_flat(proposal))
        outfile.seek(0)
        return Response(
            six.text_type(outfile.getvalue(), 'utf-8'),
            content_type='text/csv',
            headers=[
                (
                    'Content-Disposition',
                    'attachment;filename="{project}.csv"'.format(project=self.obj.name),
                )
            ],
        )

    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @lastuser.requires_login
    @requires_permission('edit_project')
    def edit(self):
        if request.method == 'GET':
            # find draft if it exists
            draft_revision, initial_formdata = self.get_draft_data()

            # initialize forms with draft initial formdata.
            # if no draft exists, initial_formdata is None. wtforms ignore formdata if it's None.
            form = ProjectForm(
                obj=self.obj,
                parent=self.obj.profile,
                model=Project,
                formdata=initial_formdata,
            )

            if not self.obj.timezone:
                form.timezone.data = current_auth.user.timezone

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

                    # find and delete draft if it exists
                    if self.get_draft() is not None:
                        self.delete_draft()
                        db.session.commit()

                    return redirect(self.obj.url_for(), code=303)
                else:
                    return render_form(
                        form=form,
                        title=_("Edit project"),
                        submit=_("Save changes"),
                        autosave=True,
                    )

    @route('cfp', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
    def cfp(self):
        form = CfpForm(obj=self.obj, model=Project)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.url_for('view_proposals'), code=303)
        return render_template('project_cfp.html.jinja2', form=form, project=self.obj)

    @route('boxoffice_data', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
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
    @lastuser.requires_login
    @requires_permission('edit_project')
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
    @lastuser.requires_login
    @requires_permission('edit_project')
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
    @lastuser.requires_login
    @requires_permission('edit_project')
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
    @lastuser.requires_login
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

    @route('rsvp_list')
    @render_with('project_rsvp_list.html.jinja2')
    @lastuser.requires_login
    @requires_permission('edit_project')
    def rsvp_list(self):
        return {'project': self.obj, 'statuses': RSVP_STATUS}

    @route('save', methods=['POST'])
    @render_with(json=True)
    @lastuser.requires_login
    @requires_permission('view')
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
            return {'status': 'ok'}
        else:
            return (
                {
                    'status': 'error',
                    'error': 'project_save_form_invalid',
                    'error_description': _(
                        "Something went wrong, please reload and try again"
                    ),
                },
                400,
            )
        return redirect(self.obj.url_for(), code=303)

    @route('admin', methods=['GET', 'POST'])
    @render_with('admin.html.jinja2')
    @lastuser.requires_login
    @requires_permission('checkin_event')
    def admin(self):
        csrf_form = forms.Form()
        if csrf_form.validate_on_submit():
            for ticket_client in self.obj.ticket_clients:
                if ticket_client and ticket_client.name.lower() in [
                    u'explara',
                    u'boxoffice',
                ]:
                    import_tickets.queue(ticket_client.id)
            flash(
                _(
                    u"Importing tickets from vendors...Refresh the page in about 30 seconds..."
                ),
                'info',
            )
            return redirect(self.obj.url_for('admin'), code=303)
        return {
            'profile': self.obj.profile,
            'project': self.obj,
            'events': self.obj.events,
            'csrf_form': csrf_form,
        }


@route('/<project>/', subdomain='<profile>')
class FunnelProjectView(ProjectView):
    pass


ProjectView.init_app(app)
FunnelProjectView.init_app(funnelapp)
