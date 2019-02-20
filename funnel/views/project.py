# -*- coding: utf-8 -*-

import unicodecsv
from cStringIO import StringIO
from flask import g, flash, redirect, Response, request, abort, current_app
from baseframe import _, forms
from baseframe.forms import render_form
from coaster.auth import current_auth
from coaster.utils import getbool
from coaster.views import jsonp, route, render_with, requires_permission, UrlForView, ModelView

from .. import app, funnelapp, lastuser
from ..models import db, Project, Section, Proposal, Rsvp, RSVP_STATUS
from ..forms import ProjectForm, SubprojectForm, RsvpForm, ProjectTransitionForm, ProjectBoxofficeForm
from ..jobs import tag_locations, import_tickets
from .proposal import proposal_headers, proposal_data, proposal_data_flat
from .schedule import schedule_data
from .venue import venue_data, room_data
from .section import section_data
from .mixins import ProjectViewMixin, ProfileViewMixin, DraftViewMixin
from .decorators import legacy_redirect


def project_data(project):
    return {
        'id': project.id,
        'name': project.name,
        'title': project.title,
        'datelocation': project.datelocation,
        'timezone': project.timezone,
        'start': project.date.isoformat() if project.date else None,
        'end': project.date_upto.isoformat() if project.date_upto else None,
        'status': project.old_state.value,
        'state': project.old_state.label.name,
        'url': project.url_for(_external=True),
        'website': project.website,
        'json_url': project.url_for('json', _external=True),
        'bg_image': project.bg_image,
        'bg_color': project.bg_color,
        'explore_url': project.explore_url,
        }


@route('/<profile>')
class ProfileProjectView(ProfileViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new_project')
    def new_project(self):
        form = ProjectForm(model=Project, parent=self.obj)
        form.parent_project.query = self.obj.projects
        if request.method == 'GET':
            form.timezone.data = current_app.config.get('TIMEZONE')
        if form.validate_on_submit():
            project = Project(user=current_auth.user, profile=self.obj)
            form.populate_obj(project)
            # Set labels with default configuration
            project.set_labels()
            db.session.add(project)
            db.session.commit()
            flash(_("Your new project has been created"), 'info')
            tag_locations.queue(project.id)
            return redirect(project.url_for(), code=303)
        return render_form(form=form, title=_("Create a new project"), submit=_("Create project"), cancel_url=self.obj.url_for())


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
        sections = Section.query.filter_by(project=self.obj, public=True).order_by('title').all()
        sections_list = [s.current_access() for s in sections]
        rsvp_form = RsvpForm(obj=self.obj.rsvp_for(g.user))
        transition_form = ProjectTransitionForm(obj=self.obj)
        return {'project': self.obj, 'sections': sections_list,
            'rsvp_form': rsvp_form, 'transition_form': transition_form}

    @route('proposals')
    @render_with('proposals.html.jinja2')
    @requires_permission('view')
    def view_proposals(self):
        return {'project': self.obj}

    @route('json')
    @render_with(json=True)
    @requires_permission('view')
    def json(self):
        sections = Section.query.filter_by(project=self.obj, public=True).order_by('title').all()
        proposals = Proposal.query.filter_by(project=self.obj).order_by(db.desc('created_at')).all()
        return jsonp(**{
            'project': project_data(self.obj),
            'space': project_data(self.obj),  # FIXME: Remove when the native app switches over
            'sections': [section_data(s) for s in sections],
            'venues': [venue_data(venue) for venue in self.obj.venues],
            'rooms': [room_data(room) for room in self.obj.rooms],
            'proposals': [proposal_data(proposal) for proposal in proposals],
            'schedule': schedule_data(self.obj),
            })

    @route('csv')
    @requires_permission('view')
    def csv(self):
        if current_auth.permissions.view_contactinfo:
            usergroups = [ug.name for ug in self.obj.usergroups]
        else:
            usergroups = []
        proposals = Proposal.query.filter_by(project=self.obj).order_by(db.desc('created_at')).all()
        outfile = StringIO()
        out = unicodecsv.writer(outfile, encoding='utf-8')
        out.writerow(proposal_headers + ['votes_' + group for group in usergroups] + ['status'])
        for proposal in proposals:
            out.writerow(proposal_data_flat(proposal, usergroups))
        outfile.seek(0)
        return Response(unicode(outfile.getvalue(), 'utf-8'), content_type='text/csv',
            headers=[('Content-Disposition', 'attachment;filename="{project}.csv"'.format(project=self.obj.name))])

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
            if self.obj.parent_project:
                form = SubprojectForm(obj=self.obj, model=Project, formdata=initial_formdata)
            else:
                form = ProjectForm(obj=self.obj, parent=self.obj.profile, model=Project, formdata=initial_formdata)

            if not self.obj.timezone:
                form.timezone.data = current_auth.user.timezone

            return render_form(form=form, title=_("Edit project"), submit=_("Save changes"), autosave=True, draft_revision=draft_revision)
        elif request.method == 'POST':
            if getbool(request.args.get('form.autosave')):
                return self.autosave_post()
            else:
                if self.obj.parent_project:
                    form = SubprojectForm(obj=self.obj, model=Project)
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
                    return render_form(form=form, title=_("Edit project"), submit=_("Save changes"), autosave=True)

    @route('add_cfp', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
    def add_cfp(self):
        # TODO: Create a CFP form and update it here
        if self.obj.parent_project:
            form = SubprojectForm(obj=self.obj, model=Project)
        else:
            form = ProjectForm(obj=self.obj, parent=self.obj.profile, model=Project)
        return render_form(form=form, title=_("Add a CFP"), submit=_("Save changes"))

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
        return render_form(form=form, title=_("Edit ticket client details"), submit=_("Save changes"))

    @route('transition', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('edit_project')
    def transition(self):
        transition_form = ProjectTransitionForm(obj=self.obj)
        if transition_form.validate_on_submit():  # check if the provided transition is valid
            transition = getattr(self.obj.current_access(),
                transition_form.transition.data)
            transition()  # call the transition
            db.session.commit()
            flash(transition.data['message'], 'success')
        else:
            flash(_("Invalid transition for this project."), 'error')
            abort(403)
        return redirect(self.obj.url_for())

    @route('rsvp', methods=['POST'])
    @render_with('rsvp.html.jinja2')
    @lastuser.requires_login
    @requires_permission('view')
    def rsvp(self):
        form = RsvpForm()
        if form.validate_on_submit():
            rsvp = Rsvp.get_for(self.obj, g.user, create=True)
            form.populate_obj(rsvp)
            db.session.commit()
            if request.is_xhr:
                return dict(project=self.obj, rsvp=rsvp, rsvp_form=form)
            else:
                return redirect(self.obj.url_for(), code=303)
        else:
            abort(400)

    @route('rsvp_list')
    @render_with('project_rsvp_list.html.jinja2')
    @lastuser.requires_login
    @requires_permission('edit_project')
    def rsvp_list(self):
        return dict(project=self.obj, statuses=RSVP_STATUS)

    @route('admin', methods=['GET', 'POST'])
    @render_with('admin.html.jinja2')
    @lastuser.requires_login
    @requires_permission('admin')
    def admin(self):
        csrf_form = forms.Form()
        if csrf_form.validate_on_submit():
            for ticket_client in self.obj.ticket_clients:
                if ticket_client and ticket_client.name.lower() in [u'explara', u'boxoffice']:
                    import_tickets.queue(ticket_client.id)
            flash(_(u"Importing tickets from vendors...Refresh the page in about 30 seconds..."), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return dict(profile=self.obj.profile, project=self.obj, events=self.obj.events, csrf_form=csrf_form)


@route('/<project>/', subdomain='<profile>')
class FunnelProjectView(ProjectView):
    pass


ProjectView.init_app(app)
FunnelProjectView.init_app(funnelapp)
