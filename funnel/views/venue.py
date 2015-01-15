# -*- coding: utf-8 -*-

from flask import flash, render_template, jsonify
from coaster.views import load_models, requestargs
from baseframe import _
from baseframe.forms import render_redirect, render_form, render_delete_sqla

from .. import app, lastuser
from ..models import db, Profile, ProposalSpace, ProposalSpaceRedirect, Venue, VenueRoom
from ..forms.venue import VenueForm, VenueRoomForm

RESERVED_VENUE = ['new']
RESERVED_VENUEROOM = ['new', 'edit', 'delete']


def venue_data(venue):
    return {
        'name': venue.name,
        'title': venue.title,
        'description': venue.description.html,
        'address1': venue.address1,
        'address2': venue.address2,
        'city': venue.city,
        'state': venue.state,
        'postcode': venue.postcode,
        'country': venue.country,
        'latitude': venue.latitude,
        'longitude': venue.longitude,
        'url': None,
        'json_url': None,
        }


def room_data(room):
    return {
        'name': room.scoped_name,
        'title': room.title,
        'description': room.description.html,
        'venue': room.venue.name,
        'bgcolor': room.bgcolor,
        'url': None,
        'json_url': None,
        }


@app.route('/<space>/venues', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def venue_list(profile, space):
    return render_template('venues.html', space=space, venues=space.venues)


@app.route('/<space>/venues/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-venue')
def venue_new(profile, space):
    form = VenueForm()
    if form.validate_on_submit():
        venue = Venue()
        form.populate_obj(venue)
        venue.proposal_space = space
        venue.make_name(reserved=RESERVED_VENUE)
        db.session.add(venue)
        db.session.commit()
        flash(_(u"You have added a new venue to the event"), 'success')
        return render_redirect(space.url_for('venues'), code=303)
    return render_form(form=form, title=_("New venue"), submit=_("Create"), cancel_url=space.url_for('venues'), ajax=False)


@app.route('/<space>/venues/<venue>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    permission='edit-venue')
def venue_edit(profile, space, venue):
    form = VenueForm(obj=venue)
    if form.validate_on_submit():
        form.populate_obj(venue)
        venue.make_name(reserved=RESERVED_VENUE)
        db.session.commit()
        flash(_(u"Saved changes to this venue"), 'success')
        return render_redirect(space.url_for('venues'), code=303)
    return render_form(form=form, title=_("Edit venue"), submit=_("Save"), cancel_url=space.url_for('venues'), ajax=False)


@app.route('/<space>/venues/<venue>/delete', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    permission='delete-venue')
def venue_delete(profile, space, venue):
    return render_delete_sqla(venue, db, title=u"Confirm delete",
        message=_(u"Delete venue “{title}”? This cannot be undone".format(title=venue.title)),
        success=_(u"You have deleted venue “{title}”".format(title=venue.title)),
        next=space.url_for('venues'))


@app.route('/<space>/venues/<venue>/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    permission='new-venue')
def venueroom_new(profile, space, venue):
    form = VenueRoomForm()
    if form.validate_on_submit():
        room = VenueRoom()
        form.populate_obj(room)
        room.venue = venue
        room.make_name(reserved=RESERVED_VENUEROOM)
        db.session.add(room)
        db.session.commit()
        flash(_(u"You have added a room at this venue"), 'success')
        return render_redirect(space.url_for('venues'), code=303)
    return render_form(form=form, title=_("New room"), submit=_("Create"), cancel_url=space.url_for('venues'), ajax=False)


@app.route('/<space>/venues/<venue>/<room>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    (VenueRoom, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='edit-venue')
def venueroom_edit(profile, space, venue, room):
    form = VenueRoomForm(obj=room)
    if form.validate_on_submit():
        form.populate_obj(room)
        room.make_name(reserved=RESERVED_VENUEROOM)
        db.session.commit()
        flash(_(u"Saved changes to this room"), 'success')
        return render_redirect(space.url_for('venues'), code=303)
    return render_form(form=form, title=_("Edit room"), submit=_("Save"), cancel_url=space.url_for('venues'), ajax=False)


@app.route('/<space>/venues/<venue>/<room>/delete', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    (VenueRoom, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='delete-venue')
def venueroom_delete(profile, space, venue, room):
    return render_delete_sqla(room, db, title=u"Confirm delete",
        message=_(u"Delete room “{title}”? This cannot be undone".format(title=room.title)),
        success=_(u"You have deleted room “{title}”".format(title=room.title)),
        next=space.url_for('venues'))


@app.route('/<space>/update_venue_colors', methods=['POST'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='edit-venue')
@requestargs('id[]', 'color[]')
def update_venue_colors(profile, space, id, color):
    colors = dict([(id[i], col.replace('#', '')) for i, col in enumerate(color)])
    for room in space.rooms:
        if room.scoped_name in colors:
            room.bgcolor = colors[room.scoped_name]
    db.session.commit()
    return jsonify(status=True)
