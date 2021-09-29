from __future__ import annotations

from typing import Optional

from sqlalchemy.exc import IntegrityError

from flask import abort, flash, jsonify, redirect, request

from baseframe import _, forms
from baseframe.forms import render_delete_sqla, render_form
from coaster.utils import getbool
from coaster.views import ModelView, UrlForView, render_with, requires_roles, route

from .. import app
from ..forms import (
    TicketClientForm,
    TicketEventForm,
    TicketParticipantBadgeForm,
    TicketTypeForm,
)
from ..models import (
    Profile,
    Project,
    SyncTicket,
    TicketClient,
    TicketEvent,
    TicketParticipant,
    TicketType,
    db,
)
from ..typing import ReturnView
from .jobs import import_tickets
from .login_session import requires_login, requires_sudo
from .mixins import ProfileCheckMixin, ProjectViewMixin, TicketEventViewMixin


@Project.views('ticket_event')
@route('/<profile>/<project>/ticket_event')
class ProjectTicketEventView(ProjectViewMixin, UrlForView, ModelView):
    @route('')
    @render_with('ticket_event_list.html.jinja2')
    @requires_login
    @requires_roles({'promoter', 'usher'})
    def ticket_events(self):
        return {
            'project': self.obj,
            'profile': self.obj.profile,
            'ticket_events': self.obj.ticket_events,
        }

    @route('json')
    @requires_login
    @requires_roles({'editor', 'promoter'})
    def events_json(self):
        return jsonify(
            ticket_events=[
                {'name': e.name, 'title': e.title} for e in self.obj.ticket_events
            ]
        )

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'promoter'})
    def new_event(self):
        form = TicketEventForm()
        if form.validate_on_submit():
            ticket_event = TicketEvent(project=self.obj)
            form.populate_obj(ticket_event)
            ticket_event.make_name()
            try:
                db.session.add(ticket_event)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(_("This event already exists"), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(form=form, title=_("New Event"), submit=_("Add event"))

    @route('ticket_type/new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'promoter'})
    def new_ticket_type(self):
        form = TicketTypeForm()
        form.ticket_events.query = self.obj.ticket_events
        if form.validate_on_submit():
            ticket_type = TicketType(project=self.obj)
            form.populate_obj(ticket_type)
            ticket_type.make_name()
            try:
                db.session.add(ticket_type)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(_("This ticket type already exists"), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(
            form=form, title=_("New Ticket Type"), submit=_("Add ticket type")
        )

    @route('ticket_client/new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'promoter'})
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
                flash(_("This ticket client already exists"), 'info')
            return redirect(self.obj.url_for('admin'), code=303)
        return render_form(
            form=form, title=_("New Ticket Client"), submit=_("Add ticket client")
        )


ProjectTicketEventView.init_app(app)


@TicketEvent.views('main')
@route('/<profile>/<project>/ticket_event/<name>')
class TicketEventView(TicketEventViewMixin, UrlForView, ModelView):
    __decorators__ = [requires_login]

    @route('', methods=['GET', 'POST'])
    @render_with('ticket_event.html.jinja2')
    @requires_roles({'project_promoter', 'project_usher'})
    def view(self):
        if request.method == 'POST':
            if 'form.id' not in request.form:
                abort(400)
            if request.form['form.id'] == 'csrf_form':
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
                            "Importing tickets from vendors…"
                            " Reload the page in about 30 seconds…"
                        ),
                        'info',
                    )
            elif request.form['form.id'] == 'badge_form':
                form = TicketParticipantBadgeForm()
                if form.validate_on_submit():
                    badge_printed = getbool(form.data.get('badge_printed'))
                    db.session.query(TicketParticipant).filter(
                        TicketParticipant.id.in_(
                            [
                                ticket_participant.id
                                for ticket_participant in self.obj.ticket_participants
                            ]
                        )
                    ).update(
                        {'badge_printed': badge_printed}, synchronize_session=False
                    )
                    db.session.commit()
                    return redirect(self.obj.url_for('view'), code=303)
            else:
                # Unknown form
                abort(400)
        return {
            'profile': self.obj.project.profile,
            'ticket_event': self.obj,
            'project': self.obj.project,
            'badge_form': TicketParticipantBadgeForm(model=TicketParticipant),
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'project_promoter'})
    def edit(self):
        form = TicketEventForm(obj=self.obj, model=TicketEvent)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.project.url_for('admin'), code=303)
        return render_form(form=form, title=_("Edit event"), submit=_("Save changes"))

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'project_promoter'})
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Delete event ‘{title}’? This operation is permanent and cannot be"
                " undone"
            ).format(title=self.obj.title),
            success=_("This event has been deleted"),
            next=self.obj.project.url_for('admin'),
            cancel_url=self.obj.url_for(),
        )

    @route('scan_badge')
    @render_with('scan_badge.html.jinja2')
    @requires_roles({'project_promoter', 'project_usher'})
    def scan_badge(self):
        return {
            'profile': self.obj.project.profile,
            'project': self.obj.project,
            'ticket_event': self.obj,
        }


TicketEventView.init_app(app)


@TicketType.views('main')
@route('/<profile>/<project>/ticket_type/<name>')
class TicketTypeView(ProfileCheckMixin, UrlForView, ModelView):
    __decorators__ = [requires_login]
    model = TicketType
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'name': 'name',
    }
    obj: TicketType

    def loader(self, profile, project, name) -> TicketType:
        return (
            TicketType.query.join(Project, Profile)
            .filter(
                db.func.lower(Profile.name) == db.func.lower(profile),
                Project.name == project,
                TicketType.name == name,
            )
            .first_or_404()
        )

    def after_loader(self) -> Optional[ReturnView]:
        self.profile = self.obj.project.profile
        return super().after_loader()

    @route('')
    @render_with('ticket_type.html.jinja2')
    @requires_roles({'project_promoter'})
    def view(self):
        ticket_participants = (
            TicketParticipant.query.join(SyncTicket)
            .filter(SyncTicket.ticket_type == self.obj)
            .all()
        )
        return {
            'profile': self.obj.project.profile,
            'project': self.obj.project,
            'ticket_type': self.obj,
            'ticket_participants': ticket_participants,
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'project_promoter'})
    def edit(self):
        form = TicketTypeForm(obj=self.obj, model=TicketType)
        form.ticket_events.query = self.obj.project.ticket_events
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.project.url_for('admin'), code=303)
        return render_form(
            form=form, title=_("Edit ticket type"), submit=_("Save changes")
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'project_promoter'})
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Delete ticket type ‘{title}’? This operation is permanent and cannot"
                " be undone"
            ).format(title=self.obj.title),
            success=_("This ticket type has been deleted"),
            next=self.obj.project.url_for('admin'),
            cancel_url=self.obj.url_for(),
        )


TicketTypeView.init_app(app)


@TicketClient.views('main')
@route('/<profile>/<project>/ticket_client/<client_id>')
class TicketClientView(ProfileCheckMixin, UrlForView, ModelView):
    __decorators__ = [requires_login]
    model = TicketClient
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'client_id': 'id',
    }
    obj: TicketClient

    def loader(self, profile, project, client_id) -> TicketClient:
        return (
            TicketClient.query.join(Project, Profile)
            .filter(
                db.func.lower(Profile.name) == db.func.lower(profile),
                Project.name == project,
                TicketClient.id == client_id,
            )
            .first_or_404()
        )

    def after_loader(self) -> Optional[ReturnView]:
        self.profile = self.obj.project.profile
        return super().after_loader()

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'project_promoter'})
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
    @requires_sudo
    @requires_roles({'project_promoter'})
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Delete ticket client ‘{title}’? This operation is permanent and cannot"
                " be undone"
            ).format(title=self.obj.name),
            success=_("This event has been deleted"),
            next=self.obj.project.url_for('admin'),
            cancel_url=self.obj.project.url_for(),
        )


TicketClientView.init_app(app)
