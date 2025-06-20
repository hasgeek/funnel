"""Views for ticketed events synced from a ticketing provider."""

from __future__ import annotations

from flask import abort, flash, request
from sqlalchemy.exc import IntegrityError

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
    Account,
    Project,
    SyncTicket,
    TicketClient,
    TicketEvent,
    TicketParticipant,
    TicketType,
    db,
)
from ..typing import ReturnRenderWith, ReturnView
from .helpers import render_redirect
from .jobs import import_tickets
from .login_session import requires_login, requires_sudo
from .mixins import AccountCheckMixin, ProjectViewBase, TicketEventViewBase


@Project.views('ticket_event')
@route('/<account>/<project>/ticket_event', init_app=app)
class ProjectTicketEventView(ProjectViewBase):
    @route('')
    @render_with('ticket_event_list.html.jinja2')
    @requires_login
    @requires_roles({'promoter', 'usher'})
    def ticket_events(self) -> ReturnRenderWith:
        return {
            'project': self.obj,
            'account': self.obj.account,
            'ticket_events': self.obj.ticket_events,
        }

    @route('json')
    @requires_login
    @requires_roles({'editor', 'promoter'})
    def events_json(self) -> ReturnView:
        return {
            'status': 'ok',
            'ticket_events': [
                {'name': e.name, 'title': e.title} for e in self.obj.ticket_events
            ],
        }

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'promoter'})
    def new_event(self) -> ReturnView:
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
            return render_redirect(self.obj.url_for('admin'))
        return render_form(form=form, title=_("New Event"), submit=_("Add event"))

    @route('ticket_type/new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'promoter'})
    def new_ticket_type(self) -> ReturnView:
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
            return render_redirect(self.obj.url_for('admin'))
        return render_form(
            form=form, title=_("New Ticket Type"), submit=_("Add ticket type")
        )

    @route('ticket_client/new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'promoter'})
    def new_ticket_client(self) -> ReturnView:
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
            return render_redirect(self.obj.url_for('admin'))
        return render_form(
            form=form, title=_("New Ticket Client"), submit=_("Add ticket client")
        )


@TicketEvent.views('main')
class TicketEventView(TicketEventViewBase):
    @route('', methods=['GET', 'POST'])
    @render_with('ticket_event.html.jinja2')
    @requires_roles({'project_promoter', 'project_usher'})
    def view(self) -> ReturnRenderWith:
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
                            import_tickets.enqueue(ticket_client.id)
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
                    return render_redirect(self.obj.url_for('view'))
            else:
                # Unknown form
                abort(400)
        return {
            'account': self.obj.project.account,
            'ticket_event': self.obj,
            'project': self.obj.project,
            'badge_form': TicketParticipantBadgeForm(model=TicketParticipant),
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'project_promoter'})
    def edit(self) -> ReturnView:
        form = TicketEventForm(obj=self.obj, model=TicketEvent)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return render_redirect(self.obj.project.url_for('admin'))
        return render_form(form=form, title=_("Edit event"), submit=_("Save changes"))

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'project_promoter'})
    def delete(self) -> ReturnView:
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
    def scan_badge(self) -> ReturnRenderWith:
        return {
            'account': self.obj.project.account,
            'project': self.obj.project,
            'ticket_event': self.obj,
        }


TicketEventView.init_app(app)


@TicketType.views('main')
@route('/<account>/<project>/ticket_type/<name>', init_app=app)
class TicketTypeView(AccountCheckMixin, UrlForView, ModelView[TicketType]):
    __decorators__ = [requires_login]
    route_model_map = {
        'account': 'project.account.urlname',
        'project': 'project.name',
        'name': 'name',
    }

    def load(self, account: str, project: str, name: str) -> ReturnView | None:
        self.obj = (
            TicketType.query.join(Project)
            .join(Account, Project.account)
            .filter(
                Account.name_is(account),
                Project.name == project,
                TicketType.name == name,
            )
            .first_or_404()
        )
        return self.after_loader()

    @property
    def account(self) -> Account:
        return self.obj.project.account

    @route('')
    @render_with('ticket_type.html.jinja2')
    @requires_roles({'project_promoter'})
    def view(self) -> ReturnRenderWith:
        ticket_participants = (
            TicketParticipant.query.join(SyncTicket)
            .filter(SyncTicket.ticket_type == self.obj)
            .all()
        )
        return {
            'account': self.obj.project.account,
            'project': self.obj.project,
            'ticket_type': self.obj,
            'ticket_participants': ticket_participants,
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'project_promoter'})
    def edit(self) -> ReturnView:
        form = TicketTypeForm(obj=self.obj, model=TicketType)
        form.ticket_events.query = self.obj.project.ticket_events
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return render_redirect(self.obj.project.url_for('admin'))
        return render_form(
            form=form, title=_("Edit ticket type"), submit=_("Save changes")
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'project_promoter'})
    def delete(self) -> ReturnView:
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


@TicketClient.views('main')
@route('/<account>/<project>/ticket_client/<client_id>', init_app=app)
class TicketClientView(AccountCheckMixin, UrlForView, ModelView[TicketClient]):
    __decorators__ = [requires_login]
    route_model_map = {
        'account': 'project.account.urlname',
        'project': 'project.name',
        'client_id': 'id',
    }

    def load(self, account: str, project: str, client_id: str) -> ReturnView | None:
        if not client_id.isdigit():
            abort(404)
        self.obj = (
            TicketClient.query.join(Project)
            .join(Account, Project.account)
            .filter(
                Account.name_is(account),
                Project.name == project,
                TicketClient.id == int(client_id),
            )
            .first_or_404()
        )
        return self.after_loader()

    @property
    def account(self) -> Account:
        return self.obj.project.account

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'project_promoter'})
    def edit(self) -> ReturnView:
        form = TicketClientForm(obj=self.obj, model=TicketClient)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return render_redirect(self.obj.project.url_for('admin'))
        return render_form(
            form=form, title=_("Edit ticket client"), submit=_("Save changes")
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'project_promoter'})
    def delete(self) -> ReturnView:
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
