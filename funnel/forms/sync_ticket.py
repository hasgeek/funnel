"""Synchronize tickets from an external service (Boxoffice, previously Explara)."""

from __future__ import annotations

import json

from flask import Markup

from baseframe import __, forms

from ..models import (
    Account,
    AccountEmail,
    Project,
    TicketClient,
    TicketEvent,
    TicketParticipant,
    db,
)
from .helpers import nullable_json_filters, validate_and_convert_json

__all__ = [
    'FORM_SCHEMA_PLACEHOLDER',
    'ProjectBoxofficeForm',
    'TicketClientForm',
    'TicketEventForm',
    'TicketParticipantBadgeForm',
    'TicketParticipantForm',
    'TicketTypeForm',
]


BOXOFFICE_DETAILS_PLACEHOLDER = {'org': 'hasgeek', 'item_collection_id': ''}

FORM_SCHEMA_PLACEHOLDER = {
    'fields': [
        {
            'name': 'field_name',
            'title': "Field label shown to user",
            'description': "An explanation for this field",
            'type': "string",
        },
        {
            'name': 'has_checked',
            'title': "I accept the terms",
            'type': 'boolean',
        },
        {
            'name': 'choice',
            'title': "Choose one",
            'type': 'select',
            'choices': ["First choice", "Second choice", "Third choice"],
        },
    ]
}


@Project.forms('boxoffice')
class ProjectBoxofficeForm(forms.Form):
    """Link a Boxoffice ticket collection to a project."""

    org = forms.StringField(
        __("Organization name"),
        filters=[forms.filters.strip()],
    )
    item_collection_id = forms.StringField(
        __("Item collection id"),
        validators=[forms.validators.AllowedIf('org')],
        filters=[forms.filters.strip()],
    )
    allow_rsvp = forms.BooleanField(
        __("Allow free registrations"),
        default=False,
    )
    is_subscription = forms.BooleanField(
        __("Paid tickets are for a subscription"),
        default=True,
    )
    has_membership = forms.BooleanField(
        __("Tickets on this project represent memberships to the account"),
        default=False,
    )
    register_button_txt = forms.StringField(
        __("Register button text"),
        filters=[forms.filters.strip()],
        description=__("Optional – Use with care to replace the button text"),
    )
    register_form_schema = forms.StylesheetField(
        __("Registration form"),
        description=__("Optional – Specify fields as JSON (limited support)"),
        filters=nullable_json_filters,
        validators=[forms.validators.Optional(), validate_and_convert_json],
    )

    def set_queries(self):
        """Set form schema description."""
        self.register_form_schema.description = Markup(
            '<p>{description}</p><pre><code>{schema}</code></pre>'
        ).format(
            description=self.register_form_schema.description,
            schema=json.dumps(FORM_SCHEMA_PLACEHOLDER, indent=2),
        )


@TicketEvent.forms('main')
class TicketEventForm(forms.Form):
    """Form for a ticketed event (a project may have multiple events)."""

    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    badge_template = forms.URLField(
        __("Badge template URL"),
        description=__("URL of background image for the badge"),
        validators=[forms.validators.Optional(), forms.validators.ValidUrl()],
    )


@TicketClient.forms('main')
class TicketClientForm(forms.Form):
    """Form for a Boxoffice client access token."""

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
    """Form for a type of ticket."""

    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    ticket_events = forms.QuerySelectMultipleField(
        __("Events"),
        widget=forms.ListWidget(),
        option_widget=forms.CheckboxInput(),
        allow_blank=True,
        get_label='title',
        query_factory=lambda: [],
    )


@TicketParticipant.forms('main')
class TicketParticipantForm(forms.Form):
    """Form for a participant in a ticket."""

    __returns__ = ('user',)
    user: Account | None = None
    edit_parent: Project

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
    ticket_events = forms.QuerySelectMultipleField(
        __("Events"),
        widget=forms.ListWidget(),
        option_widget=forms.CheckboxInput(),
        get_label='title',
        validators=[forms.validators.DataRequired("Select at least one event")],
    )

    def set_queries(self) -> None:
        """Prepare form for use."""
        self.ticket_events.query = self.edit_parent.ticket_events

    def validate(self, *args, **kwargs) -> bool:
        """Validate form."""
        result = super().validate(*args, **kwargs)
        with db.session.no_autoflush:
            accountemail = AccountEmail.get(email=self.email.data)
            if accountemail is not None:
                self.user = accountemail.account
            else:
                self.user = None
        return result


@TicketParticipant.forms('badge')
class TicketParticipantBadgeForm(forms.Form):
    """Form for participant badge status."""

    choices = [('', "Badge printing status"), ('t', "Printed"), ('f', "Not printed")]
    badge_printed = forms.SelectField(
        "", choices=[(val_title[0], val_title[1]) for val_title in choices]
    )
