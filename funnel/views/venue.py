# -*- coding: utf-8 -*-

from flask import flash
from coaster.views import load_model, load_models
from baseframe import _
from baseframe.forms import render_redirect, render_form, render_delete_sqla

from funnel import app, lastuser
from funnel.models import db, ProposalSpace, Venue, Room
from funnel.forms.venue import VenueForm, RoomForm


@app.route('/<space>/venues/new', methods=['GET', 'POST'])
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space', permission='edit-space')
def venue_new(space):
    form = VenueForm()
    if form.validate_on_submit():
        venue = Venue()
        form.populate_obj(venue)
        venue.proposal_space = space
        venue.make_name()
        db.session.add(venue)
        db.session.commit()
        flash(_("You have added a new venue to the event"), u'success')
        return render_redirect(space.url_for(), code=303)
    return render_form(form=form, title=_("New venue"), submit=_("Create"), cancel_url=space.url_for(), ajax=False)


@app.route('/<space>/venues/<venue>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    permission='edit-space')
def venue_edit(space, venue):
    form = VenueForm(obj=venue)
    if form.validate_on_submit():
        form.populate_obj(venue)
        venue.proposal_space = space
        venue.make_name()
        db.session.commit()
        flash(_("Saved changes to this venue"), u'success')
        return render_redirect(space.url_for(), code=303)
    return render_form(form=form, title=_("Edit venue"), submit=_("Edit"), cancel_url=space.url_for(), ajax=False)


@app.route('/<space>/venues/<venue>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'), permission='edit-space')
def venue_delete(space, venue):
    return render_delete_sqla(venue, db, title=u"Confirm delete",
        message=_("Delete venue '{title}'? This cannot be undone".format(title=venue.title)),
        success=_("You have deleted venue {title}".format(title=venue.title)),
        next=space.url_for())


@app.route('/<space>/venues/<venue>/new', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'), permission='edit-space')
def room_new(space, venue):
    form = RoomForm()
    if form.validate_on_submit():
        room = Room()
        form.populate_obj(room)
        room.venue = venue
        room.make_name()
        db.session.add(room)
        db.session.commit()
        flash(_("You have added a room at this venue"), u'success')
        return render_redirect(space.url_for(), code=303)
    return render_form(form=form, title=_("New room"), submit=_("Create"), cancel_url=space.url_for(), ajax=False)


@app.route('/<space>/venues/<venue>/<room>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    (Room, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='edit-space')
def room_edit(space, venue, room):
    form = RoomForm(obj=room)
    if form.validate_on_submit():
        form.populate_obj(room)
        room.venue = venue
        room.make_name()
        db.session.commit()
        flash(_("Saved changes to this room"), u'success')
        return render_redirect(space.url_for(), code=303)
    return render_form(form=form, title=_("Edit room"), submit=_("Edit"), cancel_url=space.url_for(), ajax=False)


@app.route('/<space>/venues/<venue>/<room>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    (Room, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='edit-space')
def room_delete(space, venue, room):
    return render_delete_sqla(room, db, title=u"Confirm delete",
        message=_("Delete room '{title}'? This cannot be undone".format(title=room.title)),
        success=_("You have deleted room '{title}'".format(title=room.title)),
        next=space.url_for())
