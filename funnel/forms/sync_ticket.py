from __future__ import annotations

from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms.widgets import CheckboxInput, ListWidget

from baseframe import __
import baseframe.forms as forms

from ..models import (
    Project,
    TicketClient,
    TicketEvent,
    TicketParticipant,
    UserEmail,
    db,
)

__all__ = [
    'ProjectBoxofficeForm',
    'TicketClientForm',
    'TicketEventForm',
    'TicketParticipantBadgeForm',
    'TicketParticipantForm',
    'TicketTypeForm',
]

BOXOFFICE_DETAILS_PLACEHOLDER = {'org': 'hasgeek', 'item_collection_id': ''}


@Project.forms('boxoffice')
class ProjectBoxofficeForm(forms.Form):
    boxoffice_data = forms.JsonField(
        __("Ticket client details"), default=BOXOFFICE_DETAILS_PLACEHOLDER
    )


@TicketEvent.forms('main')
class TicketEventForm(forms.Form):
    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    badge_template = forms.URLField(
        __("Badge template URL"),
        description="URL of background image for the badge",
        validators=[forms.validators.Optional(), forms.validators.ValidUrl()],
    )


@TicketClient.forms('main')
class TicketClientForm(forms.Form):
    name = forms.StringField(
        __("Name"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    clientid = forms.StringField(
        __("Client id"), validators=[forms.validators.DataRequired()]
    )
    client_eventid = forms.StringField(
        __("Client event id"), validators=[forms.validators.DataRequired()]
    )
    client_secret = forms.StringField(
        __("Client event secret"), validators=[forms.validators.DataRequired()]
    )
    client_access_token = forms.StringField(
        __("Client access token"), validators=[forms.validators.DataRequired()]
    )


@TicketEvent.forms('ticket_type')
class TicketTypeForm(forms.Form):
    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    ticket_events = QuerySelectMultipleField(
        __("Events"),
        widget=ListWidget(),
        option_widget=CheckboxInput(),
        allow_blank=True,
        get_label='title',
        query_factory=lambda: [],
    )


@TicketParticipant.forms('main')
class TicketParticipantForm(forms.Form):
    __returns__ = ('user',)

    fullname = forms.StringField(
        __("Fullname"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    email = forms.EmailField(
        __("Email"),
        validators=[forms.validators.DataRequired(), forms.validators.ValidEmail()],
        filters=[forms.filters.strip()],
    )
    phone = forms.StringField(
        __("Phone number"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
    )
    city = forms.StringField(
        __("City"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
    )
    company = forms.StringField(
        __("Company"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
    )
    job_title = forms.StringField(
        __("Job title"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
    )
    twitter = forms.StringField(
        __("Twitter"),
        validators=[forms.validators.Length(max=15)],
        filters=[forms.filters.strip()],
    )
    badge_printed = forms.BooleanField(__("Badge is printed"))
    ticket_events = QuerySelectMultipleField(
        __("Events"),
        widget=ListWidget(),
        option_widget=CheckboxInput(),
        get_label='title',
        validators=[forms.validators.DataRequired("Select at least one event")],
    )

    def set_queries(self):
        if self.edit_parent is not None:
            self.ticket_events.query = self.edit_parent.ticket_events

    def validate(self):
        result = super().validate()
        with db.session.no_autoflush:
            useremail = UserEmail.get(email=self.email.data)
            if useremail is not None:
                self.user = useremail.user
            else:
                self.user = None
        return result


@TicketParticipant.forms('badge')
class TicketParticipantBadgeForm(forms.Form):
    choices = [('', "Badge printing status"), ('t', "Printed"), ('f', "Not printed")]
    badge_printed = forms.SelectField(
        "", choices=[(val_title[0], val_title[1]) for val_title in choices]
    )
