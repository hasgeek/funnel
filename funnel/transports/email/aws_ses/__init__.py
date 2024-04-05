"""AWS SES email support."""

# MARK: Everything below this line is auto-generated using `make initpy` ---------------

from . import ses_messages, sns_notifications
from .ses_messages import (
    SesBounce,
    SesComplaint,
    SesDelivery,
    SesDeliveryDelay,
    SesEvent,
    SesProcessorAbc,
)
from .sns_notifications import (
    SnsNotificationType,
    SnsValidator,
    SnsValidatorChecks,
    SnsValidatorError,
)

__all__ = [
    "SesBounce",
    "SesComplaint",
    "SesDelivery",
    "SesDeliveryDelay",
    "SesEvent",
    "SesProcessorAbc",
    "SnsNotificationType",
    "SnsValidator",
    "SnsValidatorChecks",
    "SnsValidatorError",
    "ses_messages",
    "sns_notifications",
]
