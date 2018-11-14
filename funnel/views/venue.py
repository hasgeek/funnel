# -*- coding: utf-8 -*-

from flask import flash, render_template, jsonify
from coaster.views import load_models, requestargs
from baseframe import _
from baseframe.forms import render_redirect, render_form, render_delete_sqla

from .. import app, funnelapp, lastuser
from ..models import db, Profile, Project, ProjectRedirect, Venue, VenueRoom
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


@app.route('/<profile>/<project>/venues')
@funnelapp.route('/<project>/venues', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='view')
def venue_list(profile, project):
    return render_template('venues.html.jinja2', project=project, venues=project.venues)


@app.route('/<profile>/<project>/venues/new', methods=['GET', 'POST'])
@funnelapp.route('/<project>/venues/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='new-venue')
def venue_new(profile, project):
    form = VenueForm()
    if form.validate_on_submit():
        venue = Venue()
        form.populate_obj(venue)
        venue.project = project
        venue.make_name(reserved=RESERVED_VENUE)
        db.session.add(venue)
        db.session.commit()
        flash(_(u"You have added a new venue to the event"), 'success')
        return render_redirect(project.url_for('venues'), code=303)
    return render_form(form=form, title=_("New venue"), submit=_("Create"), cancel_url=project.url_for('venues'), ajax=False)


@app.route('/<profile>/<project>/venues/<venue>/edit', methods=['GET', 'POST'])
@funnelapp.route('/<project>/venues/<venue>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Venue, {'project': 'project', 'name': 'venue'}, 'venue'),
    permission='edit-venue')
def venue_edit(profile, project, venue):
    form = VenueForm(obj=venue)
    if form.validate_on_submit():
        form.populate_obj(venue)
        venue.make_name(reserved=RESERVED_VENUE)
        db.session.commit()
        flash(_(u"Saved changes to this venue"), 'success')
        return render_redirect(project.url_for('venues'), code=303)
    return render_form(form=form, title=_("Edit venue"), submit=_("Save"), cancel_url=project.url_for('venues'), ajax=False)


@app.route('/<profile>/<project>/venues/<venue>/delete', methods=['GET', 'POST'])
@funnelapp.route('/<project>/venues/<venue>/delete', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Venue, {'project': 'project', 'name': 'venue'}, 'venue'),
    permission='delete-venue')
def venue_delete(profile, project, venue):
    return render_delete_sqla(venue, db, title=u"Confirm delete",
        message=_(u"Delete venue “{title}”? This cannot be undone".format(title=venue.title)),
        success=_(u"You have deleted venue “{title}”".format(title=venue.title)),
        next=project.url_for('venues'))


@app.route('/<profile>/<project>/venues/<venue>/new', methods=['GET', 'POST'])
@funnelapp.route('/<project>/venues/<venue>/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Venue, {'project': 'project', 'name': 'venue'}, 'venue'),
    permission='new-venue')
def venueroom_new(profile, project, venue):
    form = VenueRoomForm()
    if form.validate_on_submit():
        room = VenueRoom()
        form.populate_obj(room)
        room.venue = venue
        room.make_name(reserved=RESERVED_VENUEROOM)
        db.session.add(room)
        db.session.commit()
        flash(_(u"You have added a room at this venue"), 'success')
        return render_redirect(project.url_for('venues'), code=303)
    return render_form(form=form, title=_("New room"), submit=_("Create"), cancel_url=project.url_for('venues'), ajax=False)


@app.route('/<profile>/<project>/venues/<venue>/<room>/edit', methods=['GET', 'POST'])
@funnelapp.route('/<project>/venues/<venue>/<room>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Venue, {'project': 'project', 'name': 'venue'}, 'venue'),
    (VenueRoom, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='edit-venue')
def venueroom_edit(profile, project, venue, room):
    form = VenueRoomForm(obj=room)
    if form.validate_on_submit():
        form.populate_obj(room)
        room.make_name(reserved=RESERVED_VENUEROOM)
        db.session.commit()
        flash(_(u"Saved changes to this room"), 'success')
        return render_redirect(project.url_for('venues'), code=303)
    return render_form(form=form, title=_("Edit room"), submit=_("Save"), cancel_url=project.url_for('venues'), ajax=False)


@app.route('/<profile>/<project>/venues/<venue>/<room>/delete', methods=['GET', 'POST'])
@funnelapp.route('/<project>/venues/<venue>/<room>/delete', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Venue, {'project': 'project', 'name': 'venue'}, 'venue'),
    (VenueRoom, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='delete-venue')
def venueroom_delete(profile, project, venue, room):
    return render_delete_sqla(room, db, title=u"Confirm delete",
        message=_(u"Delete room “{title}”? This cannot be undone".format(title=room.title)),
        success=_(u"You have deleted room “{title}”".format(title=room.title)),
        next=project.url_for('venues'))


@app.route('/<profile>/<project>/update_venue_colors', methods=['POST'])
@funnelapp.route('/<project>/update_venue_colors', methods=['POST'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='edit-venue')
@requestargs('id[]', 'color[]')
def update_venue_colors(profile, project, id, color):
    colors = dict([(id[i], col.replace('#', '')) for i, col in enumerate(color)])
    for room in project.rooms:
        if room.scoped_name in colors:
            room.bgcolor = colors[room.scoped_name]
    db.session.commit()
    return jsonify(status=True)
