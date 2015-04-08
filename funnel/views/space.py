# -*- coding: utf-8 -*-

import unicodecsv
from cStringIO import StringIO
from flask import g, flash, redirect, render_template, Response, request, make_response, abort, url_for
from baseframe import _
from baseframe.forms import render_form, render_message, FormGenerator
from coaster.views import load_models, jsonp

from .. import app, lastuser
from ..models import (db, Profile, ProposalSpace, ProposalSpaceRedirect, ProposalSpaceSection, Proposal,
    PROPOSALSTATUS, Rsvp, RSVP_STATUS, Participant)
from ..forms import ProposalSpaceForm, RsvpForm, ParticipantForm
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
@lastuser.requires_login
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
    rsvp_form = RsvpForm(obj=space.rsvp_for(g.user))
    return render_template('space.html', space=space, description=space.description, sections=sections,
        PROPOSALSTATUS=PROPOSALSTATUS, rsvp_form=rsvp_form)


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
@lastuser.requires_login
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
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def rsvp(profile, space):
    form = RsvpForm()
    if form.validate_on_submit():
        rsvp = Rsvp.get_for(space, g.user, create=True)
        form.populate_obj(rsvp)
        db.session.commit()
        if request.is_xhr:
            return make_response(render_template('rsvp.html', space=space, rsvp=rsvp, rsvp_form=form))
        else:
            return redirect(space.url_for(), code=303)
    else:
        abort(400)


@app.route('/<space>/rsvp_list', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='edit-space')
def rsvp_list(profile, space):
    return render_template('space_rsvp_list.html', space=space, statuses=RSVP_STATUS)


def participant_data(participant, space_id, full=False):
    if full:
        return {
            '_id': participant.id,
            'fullname': participant.fullname,
            'job_title': participant.job_title,
            'company': participant.company,
            'email': participant.email,
            'twitter': participant.twitter,
            'phone': participant.phone,
            'space_id': space_id
        }
    else:
        return {
            '_id': participant.id,
            'fullname': participant.fullname,
            'job_title': participant.job_title,
            'company': participant.company,
            'key': participant.key,
            'space_id': space_id
        }


@app.route('/<space>/participants/json', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def participants_json(profile, space):
    return jsonp(participants=[participant_data(participant, space.id) for participant in space.participants])


@app.route('/<space>/participants', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def participants(profile, space):
    return render_template('participants.html', profile=profile, space=space, participants=space.participants.all())


@app.route('/<space>/participants/new', methods=['GET', 'POST'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def new_participant(profile, space):
    form = ParticipantForm()
    if form.validate_on_submit():
        participant = Participant(proposal_space=space)
        form.populate_obj(participant)
        db.session.add(participant)
        db.session.commit()
        return redirect(space.url_for('participants'), code=303)
    return render_form(form=form, title=_("New Participant"), submit=_("Add Participant"))


@app.route('/<space>/participant/<participant_id>/badge', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='view')
def participant_badge(profile, space, participant):
    return participant.make_badge(space)


@app.route('/<space>/participant/<participant_id>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='view')
def participant_edit(profile, space, participant):
    form = ParticipantForm(obj=participant, model=Participant)
    if form.validate_on_submit():
        form.populate_obj(participant)
        db.session.commit()
        flash(_("Your changes have been saved"), 'info')
        return redirect(space.url_for('participants'), code=303)
    return render_form(form=form, title=_("Edit Participant"), submit=_("Save changes"))

    form = ParticipantForm()
    if form.validate_on_submit():
        participant = Participant(proposal_space=space)
        form.populate_obj(participant)
        db.session.add(participant)
        db.session.commit()
        return redirect(space.url_for('participants'), code=303)
    else:
        return render_form(form=form, title=_("New Participant"), submit=_("Add Participant"))


@app.route('/<space>/participant', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def participant(profile, space):
    participant = Participant.query.filter_by(id=request.args.get('participant_id')).first()
    if not participant:
        abort(404)
    elif participant.key == request.args.get('key'):
        # TODO: add contact
        return jsonp(participant=participant_data(participant, space.id, full=True))
    else:
        abort(401)
