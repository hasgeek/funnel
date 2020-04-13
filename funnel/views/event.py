# -*- coding: utf-8 -*-

from sqlalchemy.exc import IntegrityError

from flask import flash, g, jsonify, redirect

from baseframe import _, forms
from baseframe.forms import render_delete_sqla, render_form
from coaster.utils import getbool
from coaster.views import ModelView, UrlForView, render_with, requires_roles, route

from .. import app, funnelapp
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
from .helpers import requires_login
from .mixins import EventViewMixin, ProjectViewMixin


@route('/<profile>/<project>/events')
class ProjectEventView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('event_list.html.jinja2')
    @requires_login
    @requires_roles({'usher'})
    def events(self):
        return {
            'project': self.obj,
            'profile': self.obj.profile,
            'events': self.obj.events,
        }

    @route('json')
    @requires_login
    @requires_roles({'editor', 'concierge'})
    def events_json(self):
        return jsonify(
            events=[{'name': e.name, 'title': e.title} for e in self.obj.events]
        )

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'concierge'})
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
                flash(_("This event already exists."), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(form=form, title=_("New Event"), submit=_("Add event"))

    @route('ticket_type/new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'concierge'})
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
                flash(_("This ticket type already exists."), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(
            form=form, title=_("New Ticket Type"), submit=_("Add ticket type")
        )

    @route('ticket_client/new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'concierge'})
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
                flash(_("This ticket client already exists."), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(
            form=form, title=_("New Ticket Client"), submit=_("Add ticket client")
        )


@route('/<project>/events', subdomain='<profile>')
class FunnelProjectEventView(ProjectEventView):
    pass


ProjectEventView.init_app(app)
FunnelProjectEventView.init_app(funnelapp)


@route('/<profile>/<project>/event/<name>')
class EventView(EventViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect, requires_login]

    @route('', methods=['GET', 'POST'])
    @render_with('event.html.jinja2')
    @requires_roles({'project_concierge'})
    def view(self):
        csrf_form = forms.Form()
        if csrf_form.validate_on_submit():
            for ticket_client in self.obj.project.ticket_clients:
                if ticket_client and ticket_client.name.lower() in [
                    'explara',
                    'boxoffice',
                ]:
                    import_tickets.queue(ticket_client.id)
            flash(
                _(
                    "Importing tickets from vendors... Refresh the page in about 30 seconds..."
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
            return redirect(self.obj.url_for('view'), code=303)
        return {
            'profile': self.obj.project.profile,
            'event': self.obj,
            'project': self.obj.project,
            'badge_form': ParticipantBadgeForm(model=Participant),
            'checkin_form': forms.Form(),
            'csrf_form': csrf_form,
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'project_concierge'})
    def edit(self):
        form = EventForm(obj=self.obj, model=Event)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.project.url_for('admin'), code=303)
        return render_form(form=form, title=_("Edit event"), submit=_("Save changes"))

    @route('delete', methods=['GET', 'POST'])
    @requires_roles({'project_concierge'})
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Do you really wish to delete your event ‘{title}’? "
                "This operation is permanent and cannot be undone."
            ).format(title=self.obj.title),
            success=_("This event has been deleted"),
            next=self.obj.project.url_for('admin'),
            cancel_url=self.obj.url_for(),
        )

    @route('scan_badge')
    @render_with('scan_badge.html.jinja2')
    @requires_roles({'project_usher'})
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
    __decorators__ = [legacy_redirect, requires_login]
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
        return super(TicketTypeView, self).after_loader()

    @route('')
    @render_with('ticket_type.html.jinja2')
    @requires_roles({'project_concierge'})
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
    @requires_roles({'project_concierge'})
    def edit(self):
        form = TicketTypeForm(obj=self.obj, model=TicketType)
        form.events.query = self.obj.project.events
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.project.url_for('admin'), code=303)
        return render_form(
            form=form, title=_("Edit ticket type"), submit=_("Save changes")
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_roles({'project_concierge'})
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Do you really wish to delete the ticket type ‘{title}’? "
                "This operation is permanent and cannot be undone."
            ).format(title=self.obj.title),
            success=_("This ticket type has been deleted"),
            next=self.obj.project.url_for('admin'),
            cancel_url=self.obj.url_for(),
        )


@route('/<project>/ticket_type/<name>', subdomain='<profile>', methods=['GET'])
class FunnelTicketTypeView(TicketTypeView):
    pass


TicketTypeView.init_app(app)
FunnelTicketTypeView.init_app(funnelapp)


@route('/<profile>/<project>/ticket_client/<client_id>')
class TicketClientView(UrlForView, ModelView):
    __decorators__ = [legacy_redirect, requires_login]
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
        return super(TicketClientView, self).after_loader()

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'project_concierge'})
    def edit(self):
        form = TicketClientForm(obj=self.obj, model=TicketClient)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.project.url_for('admin'), code=303)
        return render_form(
            form=form, title=_("Edit ticket client"), submit=_("Save changes")
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_roles({'project_concierge'})
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Do you really wish to delete the ticket client ‘{title}’? "
                "This operation is permanent and cannot be undone."
            ).format(title=self.obj.name),
            success=_("This event has been deleted"),
            next=self.obj.project.url_for('admin'),
            cancel_url=self.obj.project.url_for(),
        )


@route('/<project>/ticket_client/<client_id>', subdomain='<profile>')
class FunnelTicketClientView(TicketClientView):
    pass


TicketClientView.init_app(app)
FunnelTicketClientView.init_app(funnelapp)
