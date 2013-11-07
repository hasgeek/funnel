# -*- coding: utf-8 -*-

from flask import flash, render_template
from coaster.views import load_model, load_models
from baseframe import _
from baseframe.forms import render_redirect, render_form, render_delete_sqla

from funnel import app, lastuser
from funnel.models import db, ProposalSpace, Venue, VenueRoom
from funnel.forms.venue import VenueForm, VenueRoomForm

RESERVED_VENUE = ['new']
RESERVED_VENUEROOM = ['new', 'edit', 'delete']


@app.route('/<space>/venues')
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('view', 'siteadmin'), addlperms=lastuser.permissions)
def venue_list(space):
    return render_template('venues.html', space=space, venues=space.venues,
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('venues'), _("Venues"))])


@app.route('/<space>/venues/new', methods=['GET', 'POST'])
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('new-venue', 'siteadmin'), addlperms=lastuser.permissions)
def venue_new(space):
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


@app.route('/<space>/venues/<venue>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    permission=('edit-venue', 'siteadmin'), addlperms=lastuser.permissions)
def venue_edit(space, venue):
    form = VenueForm(obj=venue)
    if form.validate_on_submit():
        form.populate_obj(venue)
        venue.make_name(reserved=RESERVED_VENUE)
        db.session.commit()
        flash(_(u"Saved changes to this venue"), 'success')
        return render_redirect(space.url_for('venues'), code=303)
    return render_form(form=form, title=_("Edit venue"), submit=_("Save"), cancel_url=space.url_for('venues'), ajax=False)


@app.route('/<space>/venues/<venue>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    permission=('delete-venue', 'siteadmin'), addlperms=lastuser.permissions)
def venue_delete(space, venue):
    return render_delete_sqla(venue, db, title=u"Confirm delete",
        message=_(u"Delete venue “{title}”? This cannot be undone".format(title=venue.title)),
        success=_(u"You have deleted venue “{title}”".format(title=venue.title)),
        next=space.url_for('venues'))


@app.route('/<space>/venues/<venue>/new', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    permission=('new-venue', 'siteadmin'), addlperms=lastuser.permissions)
def venueroom_new(space, venue):
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


@app.route('/<space>/venues/<venue>/<room>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    (VenueRoom, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission=('edit-venue', 'siteadmin'), addlperms=lastuser.permissions)
def venueroom_edit(space, venue, room):
    form = VenueRoomForm(obj=room)
    if form.validate_on_submit():
        form.populate_obj(room)
        room.make_name(reserved=RESERVED_VENUEROOM)
        db.session.commit()
        flash(_(u"Saved changes to this room"), 'success')
        return render_redirect(space.url_for('venues'), code=303)
    return render_form(form=form, title=_("Edit room"), submit=_("Save"), cancel_url=space.url_for('venues'), ajax=False)


@app.route('/<space>/venues/<venue>/<room>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    (VenueRoom, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission=('delete-venue', 'siteadmin'), addlperms=lastuser.permissions)
def venueroom_delete(space, venue, room):
    return render_delete_sqla(room, db, title=u"Confirm delete",
        message=_(u"Delete room “{title}”? This cannot be undone".format(title=room.title)),
        success=_(u"You have deleted room “{title}”".format(title=room.title)),
        next=space.url_for('venues'))
