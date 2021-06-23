from __future__ import annotations

from collections import namedtuple

from flask import url_for

from baseframe import __
import baseframe.forms as forms

from ..models import User, notification_type_registry
from ..transports import platform_transports

__all__ = [
    'transport_labels',
    'UnsubscribeForm',
    'SetNotificationPreferenceForm',
]

TransportLabels = namedtuple(
    'TransportLabels',
    [
        'title',
        'requirement',
        'requirement_action',
        'unsubscribe_form',
        'unsubscribe_description',
        'switch',
        'enabled_main',
        'enabled',
        'disabled_main',
        'disabled',
    ],
)
transport_labels = {
    'email': TransportLabels(
        title=__("Email"),
        requirement=__("To enable, add a verified email address"),
        requirement_action=lambda: url_for('add_email'),
        unsubscribe_form=__("Notify me by email"),
        unsubscribe_description=__("Uncheck this to disable all email notifications"),
        switch=__("Email notifications"),
        enabled_main=__("Enabled selected email notifications"),
        enabled=__("Enabled this email notification"),
        disabled_main=__("Disabled all email notifications"),
        disabled=__("Disabled this email notification"),
    ),
    'sms': TransportLabels(
        title=__("SMS"),
        requirement=__("To enable, add a verified phone number"),
        requirement_action=lambda: url_for('add_phone'),
        unsubscribe_form=__("Notify me by SMS"),
        unsubscribe_description=__("Uncheck this to disable all SMS notifications"),
        switch=__("SMS notifications"),
        enabled_main=__("Enabled selected SMS notifications"),
        enabled=__("Enabled this SMS notification"),
        disabled_main=__("Disabled all SMS notifications"),
        disabled=__("Disabled this SMS notification"),
    ),
    'webpush': TransportLabels(
        title=__("Browser"),
        requirement=__("To enable, allow push notifications in the browser"),
        requirement_action=lambda: None,
        unsubscribe_form=__("Notify me with browser notifications"),
        unsubscribe_description=__("Uncheck this to disable all browser notifications"),
        switch=__("Push notifications"),
        enabled_main=__("Enabled selected push notifications"),
        enabled=__("Enabled this push notification"),
        disabled_main=__("Disabled all push notifications"),
        disabled=__("Disabled this push notification"),
    ),
    'telegram': TransportLabels(
        title=__("Telegram"),
        requirement=__("To enable, link your Telegram account"),
        requirement_action=lambda: None,
        unsubscribe_form=__("Notify me on Telegram"),
        unsubscribe_description=__(
            "Uncheck this to disable all Telegram notifications"
        ),
        switch=__("Telegram notifications"),
        enabled_main=__("Enabled selected Telegram notifications"),
        enabled=__("Enabled this Telegram notification"),
        disabled_main=__("Disabled all Telegram notifications"),
        disabled=__("Disabled this Telegram notification"),
    ),
    'whatsapp': TransportLabels(
        title=__("WhatsApp"),
        requirement=__("To enable, add your WhatsApp number"),
        requirement_action=lambda: url_for('add_phone'),
        unsubscribe_form=__("Notify me on WhatsApp"),
        unsubscribe_description=__(
            "Uncheck this to disable all WhatsApp notifications"
        ),
        switch=__("WhatsApp notifications"),
        enabled_main=__("Enabled selected WhatsApp notifications"),
        enabled=__("Enabled this WhatsApp notification"),
        disabled_main=__("Disabled all WhatsApp notifications"),
        disabled=__("Disabled this WhatsApp notification"),
    ),
}


@User.forms('unsubscribe')
class UnsubscribeForm(forms.Form):
    __expects__ = ('transport', 'notification_type')

    # To consider: Replace the field's ListWidget with a GroupedListWidget, and show all
    # known notifications by category, not just the ones the user has received a
    # notification for. This will avoid a dark pattern wherein a user keeps getting
    # subscribed to new types of notifications, a problem Twitter had when they
    # attempted to engage dormant accounts by inventing new reasons to email them.
    # However, also consider that this will be a long and overwhelming list, and will
    # not help with new notification types added after the user visits this list. The
    # better option may be to set notification preferences based on previous
    # preferences. A crude form of this exists in the NotificationPreferences class,
    # but it should be smarter about defaults per category of notification.

    main = forms.BooleanField(
        __("Notify me"), description=__("Uncheck this to disable all notifications")
    )

    types = forms.SelectMultipleField(
        __("Or disable only a specific notification"),
        widget=forms.ListWidget(),
        option_widget=forms.CheckboxInput(),
    )

    # This token is validated in the view, not here, because it has to be valid in the
    # GET request itself, and the UI flow is very dependent on the validation error.
    token = forms.HiddenField(
        __("Unsubscribe token"), validators=[forms.validators.DataRequired()]
    )
    token_type = forms.HiddenField(
        __("Unsubscribe token type"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        # Populate choices with all notification types that the user has a preference
        # row for.
        if self.transport in transport_labels:
            self.main.label.text = transport_labels[self.transport].unsubscribe_form
            self.main.description = transport_labels[
                self.transport
            ].unsubscribe_description

        self.types.choices = [
            (
                ntype,
                notification_type_registry[ntype].title
                + (" 👈" if ntype == self.notification_type else ''),
            )
            for ntype in notification_type_registry
            if ntype in self.edit_obj.notification_preferences
            and notification_type_registry[ntype].allow_transport(self.transport)
        ]  # Sorted by definition order. Usable until we introduce grouping

    def get_main(self, obj):
        return obj.main_notification_preferences.by_transport(self.transport)

    def get_types(self, obj):
        # Populate data with all notification types for which the user has the
        # current transport enabled
        return [
            ntype
            for ntype, user_prefs in obj.notification_preferences.items()
            if user_prefs.by_transport(self.transport)
        ]

    def set_main(self, obj):
        obj.main_notification_preferences.set_transport(self.transport, self.main.data)

    def set_types(self, obj):
        # self.types.data will only contain the enabled preferences. Therefore, iterate
        # through all choices and toggle true or false based on whether it's in the
        # enabled list. This uses dict access instead of .get because the rows are known
        # to exist (set_queries loaded from this source).
        for ntype, _title in self.types.choices:
            obj.notification_preferences[ntype].set_transport(
                self.transport, ntype in self.types.data
            )


@User.forms('set_notification_preference')
class SetNotificationPreferenceForm(forms.Form):
    """Set one notification preference."""

    notification_type = forms.SelectField(__("Notification type"))
    transport = forms.SelectField(
        __("Transport"), validators=[forms.validators.DataRequired()]
    )
    enabled = forms.BooleanField(__("Enable this transport"))

    def set_queries(self):
        # The main switch is special-cased with an empty string for notification type
        self.notification_type.choices = [('', __("Main switch"))] + [
            (ntype, cls.title) for ntype, cls in notification_type_registry.items()
        ]
        self.transport.choices = [
            (transport, transport)
            for transport in platform_transports
            if platform_transports[transport]
        ]

    def status_message(self):
        """Render a success or error message."""
        if self.errors:
            # Flatten errors into a single string because typically this will only
            # be a CSRF error.
            return ' '.join(' '.join(message) for message in self.errors.values())
        if self.notification_type.data == '':
            return (
                transport_labels[self.transport.data].enabled_main
                if self.enabled.data
                else transport_labels[self.transport.data].disabled_main
            )
        return (
            transport_labels[self.transport.data].enabled
            if self.enabled.data
            else transport_labels[self.transport.data].disabled
        )
