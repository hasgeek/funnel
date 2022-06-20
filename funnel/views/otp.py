"""OTP support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Generic, Optional, Type, TypeVar, Union

from flask import current_app, flash, session

from baseframe import _
from coaster.utils import newpin, require_one_of

from .. import app
from ..models import (
    EmailAddress,
    SMSMessage,
    User,
    UserEmail,
    UserEmailClaim,
    UserPhone,
    db,
)
from ..transports import TransportConnectionError, TransportRecipientError, sms
from ..utils import blake2b160_hex
from .helpers import (
    delete_cached_token,
    make_cached_token,
    retrieve_cached_token,
    session_timeouts,
    validate_rate_limit,
)

session_timeouts['otp'] = timedelta(minutes=15)

# --- Exceptions -----------------------------------------------------------------------


class OtpTimeoutError(Exception):
    """Exception to indicate the OTP has expired."""


class OtpReasonError(Exception):
    """OTP is being used for a different reason than originally intended."""


# --- Typing ---------------------------------------------------------------------------

#: Tell mypy that the type of ``OtpSession.user`` is same as ``OtpSession.make(user)``.
#: We need both ``User`` and ``Optional[User]`` so that the value of ``loginform.user``
#: can be passed to :meth:`OtpSession.make`. This usage is documented in PEP 484:
#: https://peps.python.org/pep-0484/#user-defined-generic-types
OptionalUserType = TypeVar('OptionalUserType', User, Optional[User])

# --- Registry -------------------------------------------------------------------------

_reason_subclasses: Dict[str, OtpSession] = {}

# --- Classes --------------------------------------------------------------------------


@dataclass
class OtpSession(Generic[OptionalUserType]):
    """Make or retrieve an OTP in the user's cookie session."""

    reason: str
    token: str
    otp: str
    user: OptionalUserType
    email: Optional[str] = None
    phone: Optional[str] = None

    def __new__(cls, reason, **kwargs):
        """Return a subclass that contains the appropriate methods for given reason."""
        if reason not in _reason_subclasses:
            raise TypeError(f"Unknown OtpSession reason {reason}")

        use_cls = _reason_subclasses[reason]
        return super().__new__(use_cls)

    def __init_subclass__(cls, *args, **kwargs):
        """Register a subclass for use by __new__."""
        reason = kwargs.pop('reason', None)
        if not reason:
            raise TypeError("Subclasses of OtpSession must have a reason kwarg")
        super().__init_subclass__(*args, **kwargs)
        if reason in _reason_subclasses:
            raise TypeError(f"OtpSession subclass for {reason} already exists")
        _reason_subclasses[reason] = cls
        cls.reason = reason

    @classmethod
    def make(  # pylint: disable=too-many-arguments
        cls: Type[OtpSession],
        reason: str,
        user: OptionalUserType,
        anchor: Optional[Union[UserEmail, UserEmailClaim, UserPhone, EmailAddress]],
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> OtpSession:
        """
        Create an OTP for login and save it to cache and browser cookie session.

        Accepts an anchor or an explicit email address or phone number.
        """
        # Safety check, only one of anchor or phone/email can be provided
        require_one_of(anchor=anchor, phone_or_email=(phone or email))
        # Make an OTP valid for 15 minutes. Store this OTP in Redis cache and add a ref
        # to this cache entry in the user's cookie session. The cookie never contains
        # the actual OTP. See :func:`make_cached_token` for additional documentation.
        otp = newpin()
        if isinstance(anchor, UserPhone):
            phone = str(anchor)
        if isinstance(anchor, (UserEmail, UserEmailClaim, EmailAddress)):
            email = str(anchor)
        # Allow 3 OTP requests per hour per anchor. This is distinct from the rate
        # limiting for password-based login above.
        validate_rate_limit(
            'otp-send',
            ('anchor/' + blake2b160_hex(phone or email)),  # type: ignore[arg-type]
            3,
            3600,
        )
        token = make_cached_token(
            {
                'reason': reason,
                'otp': otp,
                'user_buid': user.buid if user is not None else None,
                'email': email,
                'phone': phone,
            },
            timeout=15 * 60,
        )
        session['otp'] = token
        return cls(
            reason=reason, token=token, otp=otp, user=user, email=email, phone=phone
        )

    @classmethod
    def retrieve(cls: Type[OtpSession], reason: str) -> OtpSession:
        """Retrieve an OTP from cache using the token in browser cookie session."""
        otp_token = session.get('otp')
        if not otp_token:
            raise OtpTimeoutError('cookie_expired')
        otp_data = retrieve_cached_token(otp_token)
        if not otp_data:
            raise OtpTimeoutError('cache_expired')
        if otp_data['reason'] != reason:
            raise OtpReasonError(reason)
        return cls(
            reason=reason,
            token=otp_token,
            otp=otp_data['otp'],
            user=User.get(buid=otp_data['user_buid'])
            if otp_data['user_buid']
            else None,
            email=otp_data['email'],
            phone=otp_data['phone'],
        )

    @staticmethod
    def delete() -> bool:
        """Delete OTP request from cookie session and cache."""
        token = session.pop('otp', None)
        if not token:
            return False
        delete_cached_token(token)
        return True

    def send_sms(self, render_flash: bool = True) -> Optional[SMSMessage]:
        """Send an OTP via SMS to a phone number."""
        template_message = sms.WebOtpTemplate(
            otp=self.otp,
            # TODO: Replace helpline_text with a report URL
            helpline_text=f"call {app.config['SITE_SUPPORT_PHONE']}",
            domain=current_app.config['SERVER_NAME'],
        )
        msg = SMSMessage(phone_number=self.phone, message=str(template_message))
        try:
            # Now send this
            msg.transactionid = sms.send(
                phone=msg.phone_number, message=template_message
            )
        except TransportRecipientError as exc:
            if render_flash:
                flash(str(exc), 'error')
        except TransportConnectionError:
            if render_flash:
                flash(_("Unable to send a message right now. Try again later"), 'error')
        else:
            # Commit only if an SMS could be sent
            db.session.add(msg)
            db.session.commit()
            if render_flash:
                flash(_("An OTP has been sent to your phone number"), 'success')
            return msg
        return None

    def send_email(self, render_flash: bool = True) -> Optional[str]:
        """Send an OTP via email (stub implementation)."""
        raise NotImplementedError("Subclasses must implement send_email")

    def send(self, render_flash: bool = True) -> bool:
        """Send an OTP via SMS or email."""
        if self.phone:
            success = bool(self.send_sms(render_flash))
            if success:
                return success
            # If an SMS could not be send, fallback to sending email.
        if self.email:
            return bool(self.send_email(render_flash))
        return False


def send_sms_otp(
    phone: str, otp: str, render_flash: bool = True
) -> Optional[SMSMessage]:
    """Send an OTP via SMS to a phone number."""
    template_message = sms.WebOtpTemplate(
        otp=otp,
        # TODO: Replace helpline_text with a report URL
        helpline_text=f"call {app.config['SITE_SUPPORT_PHONE']}",
        domain=current_app.config['SERVER_NAME'],
    )
    msg = SMSMessage(phone_number=phone, message=str(template_message))
    try:
        # Now send this
        msg.transactionid = sms.send(phone=msg.phone_number, message=template_message)
    except TransportRecipientError as exc:
        if render_flash:
            flash(str(exc), 'error')
    except TransportConnectionError:
        if render_flash:
            flash(_("Unable to send a message right now. Try again later"), 'error')
    else:
        # Commit only if an SMS could be sent
        db.session.add(msg)
        db.session.commit()
        if render_flash:
            flash(_("An OTP has been sent to your phone number"), 'success')
        return msg
    return None


class OtpSessionForLogin(OtpSession, reason='login'):
    # TODO
    pass


class OtpSessionForSudo(OtpSession, reason='sudo'):
    # TODO
    pass


class OtpSessionForReset(OtpSession, reason='reset'):
    # TODO
    pass
