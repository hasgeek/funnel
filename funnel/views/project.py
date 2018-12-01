# -*- coding: utf-8 -*-

import unicodecsv
from cStringIO import StringIO
from flask import g, flash, redirect, render_template, Response, request, make_response, abort, current_app
from baseframe import _
from baseframe.forms import render_form
from coaster.views import load_models, jsonp

from .. import app, funnelapp, lastuser
from ..models import (db, Profile, Project, ProjectRedirect, Section,
    Proposal, Rsvp, RSVP_STATUS)
from ..forms import ProjectForm, ProposalSubprojectForm, RsvpForm, ProjectTransitionForm
from ..jobs import tag_locations
from .proposal import proposal_headers, proposal_data, proposal_data_flat
from .schedule import schedule_data
from .venue import venue_data, room_data
from .section import section_data


def project_data(project):
    return {
        'id': project.id,
        'name': project.name,
        'title': project.title,
        'datelocation': project.datelocation,
        'timezone': project.timezone,
        'start': project.date.isoformat() if project.date else None,
        'end': project.date_upto.isoformat() if project.date_upto else None,
        'status': project.state.value,
        'state': project.state.label.name,
        'url': project.url_for(_external=True),
        'website': project.website,
        'json_url': project.url_for('json', _external=True),
        'bg_image': project.bg_image,
        'bg_color': project.bg_color,
        'explore_url': project.explore_url,
        }


@app.route('/<profile>/new', methods=['GET', 'POST'])
@funnelapp.route('/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    permission='new-project')
def project_new(profile):
    form = ProjectForm(model=Project, parent=profile)
    form.parent.query_factory = lambda: profile.projects
    if request.method == 'GET':
        form.timezone.data = current_app.config.get('TIMEZONE')
    if form.validate_on_submit():
        project = Project(user=g.user, profile=profile)
        form.populate_obj(project)
        # Set labels with default configuration
        project.set_labels()
        db.session.add(project)
        db.session.commit()
        flash(_("Your new project has been created"), 'info')
        tag_locations.delay(project.id)
        return redirect(project.url_for(), code=303)
    return render_form(form=form, title=_("Create a new project"), submit=_("Create project"), cancel_url=profile.url_for())


@app.route('/<profile>/<project>/')
@funnelapp.route('/<project>/', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='view')
def project_view(profile, project):
    sections = Section.query.filter_by(project=project, public=True).order_by('title').all()
    rsvp_form = RsvpForm(obj=project.rsvp_for(g.user))
    transition_form = ProjectTransitionForm(obj=project)
    return render_template('project.html.jinja2', project=project, description=project.description, sections=sections,
        rsvp_form=rsvp_form, transition_form=transition_form)


@app.route('/<profile>/<project>/json')
@funnelapp.route('/<project>/json', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='view')
def project_view_json(profile, project):
    sections = Section.query.filter_by(project=project, public=True).order_by('title').all()
    proposals = Proposal.query.filter_by(project=project).order_by(db.desc('created_at')).all()
    return jsonp(**{
        'project': project_data(project),
        'space': project_data(project),  # FIXME: Remove when the native app switches over
        'sections': [section_data(s) for s in sections],
        'venues': [venue_data(venue) for venue in project.venues],
        'rooms': [room_data(room) for room in project.rooms],
        'proposals': [proposal_data(proposal) for proposal in proposals],
        'schedule': schedule_data(project),
        })


@app.route('/<profile>/<project>/csv')
@funnelapp.route('/<project>/csv', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='view')
def project_view_csv(profile, project):
    if 'view-contactinfo' in g.permissions:
        usergroups = [ug.name for ug in project.usergroups]
    else:
        usergroups = []
    proposals = Proposal.query.filter_by(project=project).order_by(db.desc('created_at')).all()
    outfile = StringIO()
    out = unicodecsv.writer(outfile, encoding='utf-8')
    out.writerow(proposal_headers + ['votes_' + group for group in usergroups] + ['status'])
    for proposal in proposals:
        out.writerow(proposal_data_flat(proposal, usergroups))
    outfile.seek(0)
    return Response(unicode(outfile.getvalue(), 'utf-8'), content_type='text/csv',
        headers=[('Content-Disposition', 'attachment;filename="{project}.csv"'.format(project=project.title))])


@app.route('/<profile>/<project>/edit', methods=['GET', 'POST'])
@funnelapp.route('/<project>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='edit-project')
def project_edit(profile, project):
    if project.parent:
        form = ProposalSubprojectForm(obj=project, model=Project)
    else:
        form = ProjectForm(obj=project, model=Project)
    form.parent.query = Project.query.filter(Project.profile == profile, Project.id != project.id, Project.parent == None)
    if request.method == 'GET' and not project.timezone:
        form.timezone.data = current_app.config.get('TIMEZONE')
    if form.validate_on_submit():
        form.populate_obj(project)
        db.session.commit()
        flash(_("Your changes have been saved"), 'info')
        tag_locations.delay(project.id)
        return redirect(project.url_for(), code=303)
    return render_form(form=form, title=_("Edit project"), submit=_("Save changes"))


@app.route('/<profile>/<project>/rsvp', methods=['POST'])
@funnelapp.route('/<project>/rsvp', methods=['POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='view')
def rsvp(profile, project):
    form = RsvpForm()
    if form.validate_on_submit():
        rsvp = Rsvp.get_for(project, g.user, create=True)
        form.populate_obj(rsvp)
        db.session.commit()
        if request.is_xhr:
            return make_response(render_template('rsvp.html.jinja2', project=project, rsvp=rsvp, rsvp_form=form))
        else:
            return redirect(project.url_for(), code=303)
    else:
        abort(400)


@app.route('/<profile>/<project>/rsvp_list')
@funnelapp.route('/<project>/rsvp_list', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='edit-project')
def rsvp_list(profile, project):
    return render_template('project_rsvp_list.html.jinja2', project=project, statuses=RSVP_STATUS)


@app.route('/<profile>/<project>/transition', methods=['POST'])
@funnelapp.route('/<project>/transition', methods=['POST', ], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='edit-project')
def project_transition(profile, project):
    transition_form = ProjectTransitionForm(obj=project)
    if transition_form.validate_on_submit():  # check if the provided transition is valid
        transition = getattr(project.current_access(),
            transition_form.transition.data)
        transition()  # call the transition
        db.session.commit()
        flash(transition.data['message'], 'success')
    else:
        flash(_("Invalid transition for this project."), 'error')
        abort(403)
    return redirect(project.url_for())
