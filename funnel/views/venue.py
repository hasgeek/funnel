# -*- coding: utf-8 -*-

from flask import flash
from coaster.views import load_model, load_models
from baseframe.forms import render_redirect, render_form, render_delete_sqla

from funnel import app, lastuser
from funnel.models import db, ProposalSpace, Venue, Room
from funnel.forms.venue import VenueForm, RoomForm


@app.route('/<space>/venue/new', methods=['POST', 'GET'])
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'proposal_space', permission='edit-space')
def venue_new(proposal_space):
    form = VenueForm()
    form.proposal_space_id.choices = [(proposal_space.id, proposal_space.title)]
    if form.validate_on_submit():
        venue = Venue()
        form.populate_obj(venue)
        venue.make_name()
        db.session.add(venue)
        db.session.commit()
        flash(u"You have created a new venue for the event.", "success")
        return render_redirect(proposal_space.url_for(), code=303)
    return render_form(form=form, title="New Venue", submit=u"Create", cancel_url=proposal_space.url_for(), ajax=False)


@app.route('/<space>/venue/<venue>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'proposal_space'),
    (Venue, {'proposal_space': 'proposal_space', 'name': 'venue'}, 'venue'),
    permission='edit-space')
def venue_edit(proposal_space, venue):
    form = VenueForm(obj=venue)
    form.proposal_space_id.choices = [(proposal_space.id, proposal_space.title)]
    if form.validate_on_submit():
        form.populate_obj(venue)
        venue.make_name()
        db.session.commit()
        flash(u"Venue details are edited.", "success")
        return render_redirect(proposal_space.url_for(), code=303)
    return render_form(form=form, title="Edit Venue", submit=u"Edit", cancel_url=proposal_space.url_for(), ajax=False)


@app.route('/<space>/venue/<venue>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'proposal_space'),
    (Venue, {'proposal_space': 'proposal_space', 'name': 'venue'}, 'venue'), permission='edit-space')
def venue_delete(proposal_space, venue):
    return render_delete_sqla(venue, db, title=u"Confirm delete",
        message=u"Delete venue '%s'? This cannot be undone." % venue.title,
        success=u"You have deleted venue '%s'." % venue.title,
        next=proposal_space.url_for())


@app.route('/<space>/venue/<venue>/new', methods=['POST', 'GET'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'proposal_space'),
    (Venue, {'proposal_space': 'proposal_space', 'name': 'venue'}, 'venue'), permission='edit-space')
def room_new(proposal_space, venue):
    form = RoomForm()
    form.venue_id.choices = [(venue.id, venue.title)]
    if form.validate_on_submit():
        room = Room()
        form.populate_obj(room)
        room.make_name()
        db.session.add(room)
        db.session.commit()
        flash(u"You have created a new room for the venue.", "success")
        return render_redirect(proposal_space.url_for(), code=303)
    return render_form(form=form, title="New Room", submit=u"Create", cancel_url=proposal_space.url_for(), ajax=False)


@app.route('/<space>/venue/<venue>/<room>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'proposal_space'),
    (Venue, {'proposal_space': 'proposal_space', 'name': 'venue'}, 'venue'),
    (Room, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='edit-space')
def room_edit(proposal_space, venue, room):
    form = RoomForm(obj=room)
    form.venue_id.choices = [(venue.id, venue.title)]
    if form.validate_on_submit():
        form.populate_obj(room)
        room.make_name()
        db.session.commit()
        flash(u"Room details are edited.", "success")
        return render_redirect(proposal_space.url_for(), code=303)
    return render_form(form=form, title="Edit Room", submit=u"Edit", cancel_url=proposal_space.url_for(), ajax=False)


@app.route('/<space>/venue/<venue>/<room>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'proposal_space'),
    (Venue, {'proposal_space': 'proposal_space', 'name': 'venue'}, 'venue'),
    (Room, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='edit-space')
def room_delete(proposal_space, venue, room):
    return render_delete_sqla(room, db, title=u"Confirm delete",
        message=u"Delete room '%s'? This cannot be undone." % room.title,
        success=u"You have deleted room '%s'." % room.title,
        next=proposal_space.url_for())

