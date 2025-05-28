"""Project starting notification."""

from __future__ import annotations

from datetime import datetime

from flask import render_template

from baseframe import _, __
from baseframe.filters import time_filter

from ...models import (
    Project,
    ProjectStartingNotification,
    ProjectTomorrowNotification,
    Session,
    Venue,
)
from ...transports.sms import SmsPriority, SmsTemplate
from ..helpers import sms_shortlink
from ..notification import RenderNotification
from .mixins import TemplateVarMixin


class ProjectStartingTemplate(TemplateVarMixin, SmsTemplate):
    """DLT registered template for project starting notification."""

    registered_template = (
        'Reminder: {#var#} is starting soon. Join at {#var#}'
        '\n\nhttps://bye.li to stop - Hasgeek'
    )
    template = (
        "Reminder: {project} is starting soon. Join at {url}"
        "\n\nhttps://bye.li to stop - Hasgeek"
    )
    plaintext_template = "Reminder: {project} is starting soon. Join at {url}"
    message_priority = SmsPriority.IMPORTANT

    url: str


class ProjectStartingTomorrowVenueTemplate(TemplateVarMixin, SmsTemplate):
    """DLT registered template for in-person event notification."""

    registered_template = (
        'Reminder: {#var#} has an in-person event tomorrow at {#var#}.'
        ' Details here: {#var#}\n\nhttps://bye.li to stop -Hasgeek'
    )
    template = (
        'Reminder: {account} has an in-person event tomorrow at {venue}.'
        ' Details here: {url}\n\nhttps://bye.li to stop -Hasgeek'
    )
    plaintext_template = (
        'Reminder: {account} has an in-person event tomorrow at {venue}.'
        ' Details here: {url}'
    )
    message_priority = SmsPriority.NORMAL

    url: str


class ProjectStartingTomorrowLocationTemplate(TemplateVarMixin, SmsTemplate):
    """DLT registered template for in-person event notification."""

    registered_template = (
        'Reminder: {#var#} has an in-person event tomorrow in {#var#}.'
        ' Details here: {#var#}\n\nhttps://bye.li to stop -Hasgeek'
    )
    template = (
        'Reminder: {account} has an in-person event tomorrow in {location}.'
        ' Details here: {url}\n\nhttps://bye.li to stop -Hasgeek'
    )
    plaintext_template = (
        'Reminder: {account} has an in-person event tomorrow in {location}.'
        ' Details here: {url}'
    )
    message_priority = SmsPriority.NORMAL

    location: str
    url: str

    def truncate(self) -> None:
        """Truncate location to fit within template size limit."""
        if len(self.location) > self.var_max_length:
            self.location = self.location[: self.var_max_length - 1] + '…'


@ProjectStartingNotification.renderer
class RenderProjectStartingNotification(RenderNotification):
    """Notify crew and participants when the project's schedule is about to start."""

    project: Project
    session: Session | None
    aliases = {'document': 'project', 'fragment': 'session'}
    emoji_prefix = "⏰ "
    reason = __("You are receiving this because you have registered for this session")
    hero_image = 'img/email/chars-v1/session-starting.png'
    email_heading = __("Session starting soon!")

    @property
    def start_time(self) -> datetime | None:
        return (self.session or self.project).start_at_localized

    @property
    def venue(self) -> Venue | None:
        return (
            self.session.venue_room.venue
            if self.session and self.session.venue_room
            else self.project.primary_venue
        )

    def web(self) -> str:
        return render_template(
            'notifications/project_starting_web.html.jinja2', view=self
        )

    def email_subject(self) -> str:
        start_time = (self.session or self.project).start_at_localized
        if start_time is not None:
            return self.emoji_prefix + _("{project} starts at {time}").format(
                project=self.project.joined_title, time=time_filter(start_time)
            )
        return self.emoji_prefix + _("{project} is starting soon").format(
            project=self.project.joined_title
        )

    def email_content(self) -> str:
        return render_template(
            'notifications/project_starting_email.html.jinja2', view=self
        )

    def sms(self) -> SmsTemplate:
        return ProjectStartingTemplate(
            project=self.project,
            url=sms_shortlink(
                self.project.url_for(_external=True, **self.tracking_tags('sms'))
            ),
        )


@ProjectTomorrowNotification.renderer
class RenderProjectTomorrowNotification(RenderProjectStartingNotification):
    """Renderer for previous-day notice of an in-person session."""

    email_heading = __("In-person session tomorrow!")

    def web(self) -> str:
        return render_template(
            'notifications/project_tomorrow_web.html.jinja2', view=self
        )

    def email_subject(self) -> str:
        start_time = self.start_time
        if start_time is not None:
            return self.emoji_prefix + _("{project} starts at {time}").format(
                project=self.project.joined_title, time=time_filter(start_time)
            )
        return self.emoji_prefix + _("{project} is starting soon").format(
            project=self.project.joined_title
        )

    def email_content(self) -> str:
        return render_template(
            'notifications/project_tomorrow_email.html.jinja2', view=self
        )

    def sms(self) -> SmsTemplate:
        venue = self.venue
        if venue is not None:
            return ProjectStartingTomorrowVenueTemplate(
                account=self.project.account,
                venue=venue,
                url=sms_shortlink(
                    self.project.url_for(_external=True, **self.tracking_tags('sms'))
                ),
            )
        return ProjectStartingTomorrowLocationTemplate(
            account=self.project.account,
            location=self.project.location,
            url=sms_shortlink(
                self.project.url_for(_external=True, **self.tracking_tags('sms'))
            ),
        )
