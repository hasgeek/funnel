"""Email transport support."""

__protected__ = ['aws_ses']

# MARK: Everything below this line is auto-generated using `make initpy` ---------------

from . import aws_ses, send
from .send import (
    EmailAttachment,
    jsonld_confirm_action,
    jsonld_event_reservation,
    jsonld_view_action,
    process_recipient,
    send_email,
)

__all__ = [
    "EmailAttachment",
    "aws_ses",
    "jsonld_confirm_action",
    "jsonld_event_reservation",
    "jsonld_view_action",
    "process_recipient",
    "send",
    "send_email",
]
