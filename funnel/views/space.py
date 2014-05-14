# -*- coding: utf-8 -*-

import unicodecsv
from cStringIO import StringIO
from flask import g, flash, redirect, render_template, Response, request, jsonify
from baseframe import _
from coaster.views import load_models, jsonp, requestargs

from .. import app, lastuser
from ..models import db, Profile, ProposalSpace, ProposalSpaceSection, Proposal, PROPOSALSTATUS
from ..forms import ProposalSpaceForm
from .proposal import proposal_headers, proposal_data, proposal_data_flat
from .schedule import schedule_data
from .venue import venue_data, room_data
from .section import section_data


def space_data(space):
    return {
        'name': space.name,
        'title': space.title,
        'datelocation': space.datelocation,
        'timezone': space.timezone,
        'start': space.date.isoformat() if space.date else None,
        'end': space.date_upto.isoformat() if space.date_upto else None,
        'status': space.status,
        'url': space.url_for(_external=True),
        'json_url': space.url_for('json', _external=True),
        }


@app.route('/new', methods=['GET', 'POST'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    permission='new-space')
def space_new(profile):
    form = ProposalSpaceForm(model=ProposalSpace)
    if request.method == 'GET':
        form.timezone.data = app.config.get('TIMEZONE')
    if form.validate_on_submit():
        space = ProposalSpace(user=g.user)
        space.content = form.content.data
        form.populate_obj(space)
        db.session.add(space)
        db.session.commit()
        flash(_("Your new space has been created"), 'info')
        return redirect(space.url_for(), code=303)
    return render_template('baseframe/autoform.html', form=form, title=_("Create a new proposal space"), submit=_("Create space"))



@app.route('/<space>/', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    (ProposalSpace, {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view', addlperms=lastuser.permissions)
def space_view(profile, space):
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space, public=True).order_by('title').all()
    return render_template('space.html', space=space, description=space.description, sections=sections,
        is_siteadmin=lastuser.has_permission('siteadmin'), PROPOSALSTATUS=PROPOSALSTATUS)


@app.route('/<space>/json', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    (ProposalSpace, {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view', addlperms=lastuser.permissions)
def space_view_json(profile, space):
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space, public=True).order_by('title').all()
    proposals = Proposal.query.filter_by(proposal_space=space).order_by(db.desc('created_at')).all()
    return jsonp(**{
        'space': space_data(space),
        'sections': [section_data(s) for s in sections],
        'venues': [venue_data(venue) for venue in space.venues],
        'rooms': [room_data(room) for room in space.rooms],
        'proposals': [proposal_data(proposal) for proposal in proposals],
        'schedule': schedule_data(space),
        })


@app.route('/<space>/csv', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    (ProposalSpace, {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view', addlperms=lastuser.permissions)
def space_view_csv(profile, space):
    if lastuser.has_permission('siteadmin'):
        usergroups = [g.name for g in space.usergroups]
    else:
        usergroups = []
    proposals = Proposal.query.filter_by(proposal_space=space).order_by(db.desc('created_at')).all()
    outfile = StringIO()
    out = unicodecsv.writer(outfile, encoding='utf-8')
    out.writerow(proposal_headers + ['votes_' + group for group in usergroups] + ['status'])
    for proposal in proposals:
        out.writerow(proposal_data_flat(proposal, usergroups))
    outfile.seek(0)
    return Response(unicode(outfile.getvalue(), 'utf-8'), mimetype='text/plain')


@app.route('/<space>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    (ProposalSpace, {'name': 'space', 'profile': 'profile'}, 'space'),
    permission=('edit-space', 'siteadmin'), addlperms=lastuser.permissions)
def space_edit(profile, space):
    form = ProposalSpaceForm(obj=space, model=ProposalSpace)
    if request.method == 'GET' and not space.timezone:
        form.timezone.data = app.config.get('TIMEZONE')
    if form.validate_on_submit():
        space.content = form.content.data
        form.populate_obj(space)
        db.session.commit()
        flash(_("Your changes have been saved"), 'info')
        return redirect(space.url_for(), code=303)
    return render_template('baseframe/autoform.html', form=form, title=_("Edit proposal space"), submit=_("Save changes"))


@app.route('/<space>/update_venue_colors', methods=['POST'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    (ProposalSpace, {'name': 'space', 'profile': 'profile'}, 'space'),
    permission=('siteadmin'), addlperms=lastuser.permissions)
@requestargs('id[]', 'color[]')
def update_venue_colors(profile, space, id, color):
    colors = dict([(id[i], col.replace('#', '')) for i, col in enumerate(color)])
    for room in space.rooms:
        if room.scoped_name in colors:
            room.bgcolor = colors[room.scoped_name]
    db.session.commit()
    return jsonify(status=True)
