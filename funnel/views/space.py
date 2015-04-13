# -*- coding: utf-8 -*-

import unicodecsv
from cStringIO import StringIO
from flask import g, flash, redirect, render_template, Response, request, make_response, abort
from baseframe import _
from baseframe.forms import render_form, render_message, FormGenerator
from coaster.views import load_models, jsonp

from .. import app, lastuser
from ..models import (db, Profile, ProposalSpace, ProposalSpaceRedirect, ProposalSpaceSection, Proposal,
    PROPOSALSTATUS, Rsvp, RSVP_STATUS, Participant, Event, Attendee)
from ..forms import ProposalSpaceForm, RsvpForm, ParticipantForm
from .proposal import proposal_headers, proposal_data, proposal_data_flat
from .schedule import schedule_data
from .venue import venue_data, room_data
from .section import section_data
from helpers import split_name, format_twitter, make_qrcode


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
        PROPOSALSTATUS=PROPOSALSTATUS, rsvp_form=rsvp_form, events=space.events.all())


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
            '_id': participant.puk,
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
            '_id': participant.puk,
            'fullname': participant.fullname,
            'job_title': participant.job_title,
            'company': participant.company,
            'space_id': space_id
        }


@app.route('/<space>/participants/json', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def participants_json(profile, space):
    return jsonp(participants=[participant_data(participant, space.id) for participant in space.participants])


@app.route('/<space>/participants/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-participant')
def new_participant(profile, space):
    form = ParticipantForm()
    if form.validate_on_submit():
        participant = Participant(proposal_space=space)
        form.populate_obj(participant)
        db.session.add(participant)
        db.session.commit()
        return redirect(space.url_for(), code=303)
    return render_form(form=form, title=_("New Participant"), submit=_("Add Participant"))


@app.route('/<space>/participant/<participant_id>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='participant-edit')
def participant_edit(profile, space, participant):
    form = ParticipantForm(obj=participant, model=Participant)
    if form.validate_on_submit():
        form.populate_obj(participant)
        db.session.commit()
        flash(_("Your changes have been saved"), 'info')
        return redirect(space.url_for(), code=303)
    return render_form(form=form, title=_("Edit Participant"), submit=_("Save changes"))


@app.route('/<space>/participant', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def participant(profile, space):
    participant = Participant.query.filter_by(puk=request.args.get('participant_id')).first()
    if not participant:
        abort(404)
    elif participant.key == request.args.get('key'):
        # TODO: add contact
        return jsonp(participant=participant_data(participant, space.id, full=True))
    else:
        abort(401)


@app.route('/<space>/event', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='event-view')
def events(profile, space):
    return render_template('events.html', profile=profile, space=space, events=space.events.all())


@app.route('/<space>/event/<event_id>', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'id': 'event_id'}, 'event'),
    permission='event-view')
def event(profile, space, event):
    participants = Participant.get_by_event(event)
    return render_template('event.html', profile=profile, space=space, participants=participants, event=event)


def participant_badge_data(participants, space):
    badges = []
    for participant in participants:
        qrcode_data = "{0}{1}".format(participant.puk, participant.key)
        qrcode_path = "{0}/{1}_{2}_{3}.{4}".format(app.config.get('BADGES_PATH'), space.profile.name, space.name, str(participant.puk), 'svg')
        first_name, last_name = split_name(participant.fullname)
        badges.append({
            'first_name': first_name,
            'last_name': last_name,
            'twitter': format_twitter(participant.twitter),
            'company': participant.company,
            'qrcode_content': make_qrcode(qrcode_data, qrcode_path)
        })
    return badges


@app.route('/<space>/event/<event_id>/badges', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'id': 'event_id'}, 'event'),
    permission='event-view')
def event_badges(profile, space, event):
    if request.args.get('badge_printed') == 't':
        badge_printed = 't'
    elif request.args.get('badge_printed') == 'f':
        badge_printed = 'f'
    else:
        badge_printed = None
    participants = Participant.get_by_event(event, badge_printed)
    return render_template('badge.html', badges=participant_badge_data(participants, space))


@app.route('/<space>/participant/<participant_id>/badge', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='participant-view')
def participant_badge(profile, space, participant):
    return render_template('badge.html', badges=participant_badge_data([participant], space))


@app.route('/<space>/event/<event_id>/checkin/<participant_id>', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Event, {'id': 'event_id'}, 'event'),
    (Participant, {'id': 'participant_id'}, 'participant'),
    permission='event-checkin')
def event_checkin(profile, space, event, participant):
    a = Attendee.query.filter_by(participant_id=participant.id, event_id=event.id).first()
    checked_in = True if request.args.get('checkin') == 't' else False
    a.checked_in = checked_in
    db.session.add(a)
    db.session.commit()
    return redirect("{0}event/{1}".format(space.url_for(), event.id), code=303)
