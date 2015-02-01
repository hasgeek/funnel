# -*- coding: utf-8 -*-

import unicodecsv
from cStringIO import StringIO
from flask import g, flash, redirect, render_template, Response, request, make_response
from baseframe import _
from baseframe.forms import render_form, render_message, FormGenerator
from coaster.views import load_models, jsonp

from .. import app
from ..models import db, Profile, ProposalSpace, ProposalSpaceRedirect, ProposalSpaceSection, Proposal, PROPOSALSTATUS, Rsvp
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
        'website': space.website,
        'json_url': space.url_for('json', _external=True),
        'bg_image': space.bg_image,
        'bg_color': space.bg_color,
        'explore_url': space.explore_url,
        }


# Test endpoint
@app.route('/form', methods=['GET', 'POST'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    permission='view')
def space_form_test(profile):
    fields = [{
        'name': 'test',
        'label': 'Test Field',
        'validators': ['Required'],
    }, {
        'name': 'phone',
        'type': 'AnnotatedTextField',
        'prefix': '+91',
    }]
    form = FormGenerator().generate(fields)()
    if form.validate_on_submit():
        class Target(object):
            pass
        target = Target()
        form.populate_obj(target)
        return render_message("Form submit", "Form content: " + repr(target.__dict__))
    return render_form(form=form, title=_("Test form"), submit=_("Test submit"), cancel_url=profile.url_for())


@app.route('/new', methods=['GET', 'POST'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    permission='new-space')
def space_new(profile):
    form = ProposalSpaceForm(model=ProposalSpace)
    if request.method == 'GET':
        form.timezone.data = app.config.get('TIMEZONE')
    if form.validate_on_submit():
        space = ProposalSpace(user=g.user, profile=profile)
        form.populate_obj(space)
        db.session.add(space)
        db.session.commit()
        flash(_("Your new space has been created"), 'info')
        return redirect(space.url_for(), code=303)
    return render_form(form=form, title=_("Create a new proposal space"), submit=_("Create space"), cancel_url=profile.url_for())


@app.route('/<space>/', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def space_view(profile, space):
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space, public=True).order_by('title').all()
    return render_template('space.html', space=space, description=space.description, sections=sections,
        PROPOSALSTATUS=PROPOSALSTATUS, rsvp_actions=Rsvp.rsvp_actions(space), user_rsvp_status=Rsvp.user_rsvp_status(space, g.user))


@app.route('/<space>/json', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
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
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def space_view_csv(profile, space):
    if 'view-contactinfo' in g.permissions:
        usergroups = [ug.name for ug in space.usergroups]
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
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='edit-space')
def space_edit(profile, space):
    form = ProposalSpaceForm(obj=space, model=ProposalSpace)
    if request.method == 'GET' and not space.timezone:
        form.timezone.data = app.config.get('TIMEZONE')
    if form.validate_on_submit():
        form.populate_obj(space)
        db.session.commit()
        flash(_("Your changes have been saved"), 'info')
        return redirect(space.url_for(), code=303)
    return render_form(form=form, title=_("Edit proposal space"), submit=_("Save changes"))


@app.route('/<space>/rsvp', methods=['POST'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def rsvp(profile, space):
    rsvp = Rsvp.query.get((space.id, g.user.id))
    if rsvp:
        rsvp.rsvp_action = request.form['rsvp_action']
    else:
        rsvp = Rsvp(proposal_space=space, user=g.user, rsvp_action=request.form['rsvp_action'])
        db.session.add(rsvp)
    db.session.commit()
    return make_response(render_template('rsvp.html', space=space, rsvp=rsvp, rsvp_actions=Rsvp.rsvp_actions(space), user_rsvp_status=Rsvp.user_rsvp_status(space, g.user)))
