# -*- coding: utf-8 -*-

from sqlalchemy.exc import IntegrityError

from flask import flash, g, jsonify, redirect, url_for

from baseframe import _, forms
from baseframe.forms import render_form
from coaster.utils import getbool
from coaster.views import ModelView, UrlForView, render_with, requires_permission, route

from .. import app, funnelapp, lastuser
from ..forms import EventForm, ParticipantBadgeForm, TicketClientForm, TicketTypeForm
from ..jobs import import_tickets
from ..models import (
    Event,
    Participant,
    Profile,
    Project,
    SyncTicket,
    TicketClient,
    TicketType,
    db,
)
from .decorators import legacy_redirect
from .project import ProjectViewMixin


@route('/<profile>/<project>/events')
class ProjectEventView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('event_list.html.jinja2')
    @lastuser.requires_login
    @requires_permission('checkin_event')
    def events(self):
        return {
            'project': self.obj,
            'profile': self.obj.profile,
            'events': self.obj.events,
        }

    @route('json')
    @lastuser.requires_login
    @requires_permission('admin')
    def events_json(self):
        return jsonify(
            events=[{'name': e.name, 'title': e.title} for e in self.obj.events]
        )

    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new-event')
    def new_event(self):
        form = EventForm()
        if form.validate_on_submit():
            event = Event(project=self.obj)
            form.populate_obj(event)
            event.make_name()
            try:
                db.session.add(event)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(_(u"This event already exists."), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(form=form, title=_(u"New Event"), submit=_(u"Add Event"))

    @route('ticket_type/new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new-ticket-type')
    def new_ticket_type(self):
        form = TicketTypeForm()
        form.events.query = self.obj.events
        if form.validate_on_submit():
            ticket_type = TicketType(project=self.obj)
            form.populate_obj(ticket_type)
            ticket_type.make_name()
            try:
                db.session.add(ticket_type)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(_(u"This ticket type already exists."), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(
            form=form, title=_(u"New Ticket Type"), submit=_(u"Add ticket type")
        )

    @route('ticket_client/new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new_ticket_client')
    def new_ticket_client(self):
        form = TicketClientForm()
        if form.validate_on_submit():
            ticket_client = TicketClient(project=self.obj)
            form.populate_obj(ticket_client)
            try:
                db.session.add(ticket_client)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(_(u"This ticket client already exists."), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(
            form=form, title=_(u"New Ticket Client"), submit=_(u"Add Ticket Client")
        )


@route('/<project>/events', subdomain='<profile>')
class FunnelProjectEventView(ProjectEventView):
    pass


ProjectEventView.init_app(app)
FunnelProjectEventView.init_app(funnelapp)


@route('/<profile>/<project>/event/<name>')
class EventView(UrlForView, ModelView):
    __decorators__ = [legacy_redirect, lastuser.requires_login]
    model = Event
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'name': 'name',
    }

    def loader(self, profile, project, name):
        event = (
            self.model.query.join(Project, Profile)
            .filter(
                Profile.name == profile, Project.name == project, Event.name == name
            )
            .first_or_404()
        )
        return event

    def after_loader(self):
        g.profile = self.obj.project.profile
        super(EventView, self).after_loader()

    @route('')
    @render_with('event.html.jinja2')
    @requires_permission('checkin_event')
    def view(self):
        csrf_form = forms.Form()
        if csrf_form.validate_on_submit():
            for ticket_client in self.obj.project.ticket_clients:
                if ticket_client and ticket_client.name.lower() in [
                    u'explara',
                    u'boxoffice',
                ]:
                    import_tickets.queue(ticket_client.id)
            flash(
                _(
                    u"Importing tickets from vendors... Refresh the page in about 30 seconds..."
                ),
                'info',
            )
        form = ParticipantBadgeForm()
        if form.validate_on_submit():
            badge_printed = True if getbool(form.data.get('badge_printed')) else False
            db.session.query(Participant).filter(
                Participant.id.in_(
                    [participant.id for participant in self.obj.participants]
                )
            ).update({'badge_printed': badge_printed}, False)
            db.session.commit()
            return redirect(
                url_for(
                    'event',
                    profile=self.obj.project.profile.name,
                    project=self.obj.project.name,
                    name=self.obj.name,
                ),
                code=303,
            )
        return {
            'profile': self.obj.project.profile,
            'event': self.obj,
            'project': self.obj.project,
            'badge_form': ParticipantBadgeForm(model=Participant),
            'checkin_form': forms.Form(),
            'csrf_form': csrf_form,
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_permission('edit_event')
    def edit(self):
        form = EventForm(obj=self.obj, model=Event)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_(u"Your changes have been saved"), 'info')
            return redirect(self.obj.project.url_for('admin'), code=303)
        return render_form(form=form, title=_(u"Edit event"), submit=_(u"Save changes"))

    @route('scan_badge')
    @render_with('scan_badge.html.jinja2')
    @requires_permission('checkin_event')
    def scan_badge(self):
        return {
            'profile': self.obj.project.profile,
            'project': self.obj.project,
            'event': self.obj,
        }


@route('/<project>/event/<name>', subdomain='<profile>')
class FunnelEventView(EventView):
    pass


EventView.init_app(app)
FunnelEventView.init_app(funnelapp)


@route('/<profile>/<project>/ticket_type/<name>')
class TicketTypeView(UrlForView, ModelView):
    __decorators__ = [legacy_redirect, lastuser.requires_login]
    model = TicketType
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'name': 'name',
    }

    def loader(self, profile, project, name):
        ticket_type = (
            self.model.query.join(Project, Profile)
            .filter(
                Profile.name == profile,
                Project.name == project,
                TicketType.name == name,
            )
            .first_or_404()
        )
        return ticket_type

    def after_loader(self):
        g.profile = self.obj.project.profile
        super(TicketTypeView, self).after_loader()

    @route('')
    @render_with('ticket_type.html.jinja2')
    @requires_permission('view_ticket_type')
    def view(self):
        participants = (
            Participant.query.join(SyncTicket)
            .filter(SyncTicket.ticket_type == self.obj)
            .all()
        )
        return {
            'profile': self.obj.project.profile,
            'project': self.obj.project,
            'ticket_type': self.obj,
            'participants': participants,
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_permission('edit_event')
    def edit(self):
        form = TicketTypeForm(obj=self.obj, model=TicketType)
        form.events.query = self.obj.project.events
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_(u"Your changes have been saved"), 'info')
            return redirect(self.obj.project.url_for('admin'), code=303)
        return render_form(
            form=form, title=_(u"Edit ticket type"), submit=_(u"Save changes")
        )


@route('/<project>/ticket_type/<name>', subdomain='<profile>', methods=['GET'])
class FunnelTicketTypeView(TicketTypeView):
    pass


TicketTypeView.init_app(app)
FunnelTicketTypeView.init_app(funnelapp)


@route('/<profile>/<project>/ticket_client/<client_id>')
class TicketClientView(UrlForView, ModelView):
    __decorators__ = [legacy_redirect, lastuser.requires_login]
    model = TicketClient
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'client_id': 'id',
    }

    def loader(self, profile, project, client_id):
        ticket_client = (
            self.model.query.join(Project, Profile)
            .filter(
                Profile.name == profile,
                Project.name == project,
                TicketClient.id == client_id,
            )
            .first_or_404()
        )
        return ticket_client

    def after_loader(self):
        g.profile = self.obj.project.profile
        super(TicketClientView, self).after_loader()

    @route('edit', methods=['GET', 'POST'])
    @requires_permission('edit_ticket_client')
    def edit(self):
        form = TicketClientForm(obj=self.obj, model=TicketClient)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_(u"Your changes have been saved"), 'info')
            return redirect(self.obj.project.url_for('admin'), code=303)
        return render_form(
            form=form, title=_(u"Edit ticket client"), submit=_(u"Save changes")
        )


@route('/<project>/ticket_client/<name>', subdomain='<profile>')
class FunnelTicketClientView(TicketClientView):
    pass


TicketClientView.init_app(app)
FunnelTicketClientView.init_app(funnelapp)
