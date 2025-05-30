"""Support for OTPs using Redis cache and browser session cookie."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Generic, Self, TypeVar

import phonenumbers
from flask import current_app, flash, render_template, request, session, url_for
from werkzeug.exceptions import Forbidden, RequestTimeout, TooManyRequests
from werkzeug.utils import cached_property

from baseframe import _
from coaster.utils import newpin, require_one_of

from .. import app
from ..auth import current_auth
from ..models import (
    Account,
    AccountEmail,
    AccountEmailClaim,
    AccountPhone,
    Anchor,
    EmailAddress,
    EmailAddressBlockedError,
    PhoneNumber,
    PhoneNumberBlockedError,
    SmsMessage,
    db,
)
from ..serializers import token_serializer
from ..transports import (
    TransportConnectionError,
    TransportRecipientError,
    TransportTransactionError,
    sms,
)
from ..transports.email import jsonld_view_action, send_email
from ..utils import blake2b160_hex, mask_email, mask_phone
from .helpers import (
    delete_cached_token,
    make_cached_token,
    retrieve_cached_token,
    session_timeouts,
    str_pw_set_at,
    validate_rate_limit,
)

session_timeouts['otp'] = timedelta(minutes=15)

# MARK: Exceptions ---------------------------------------------------------------------


class OtpError(Exception):
    """Base class for OTP errors."""


class OtpTimeoutError(OtpError, RequestTimeout):
    """Exception to indicate the OTP has expired (from cache or cookie)."""


class OtpReasonError(OtpError, Forbidden):
    """OTP is being used for a different reason than originally intended."""


class OtpUserError(OtpError, Forbidden):
    """OTP is being used by a different user."""


# MARK: Typing -------------------------------------------------------------------------

#: Tell mypy that the type of ``OtpSession.user`` is same as ``OtpSession.make(user)``.
#: We need both ``Account`` and ``Account | None`` so that the value of
#: ``loginform.user``  can be passed to :meth:`OtpSession.make`. This usage is
#: documented in PEP 484: https://peps.python.org/pep-0484/#user-defined-generic-types
OptionalAccountType = TypeVar('OptionalAccountType', Account, Account | None)
#: Define type for subclasses
OtpSessionType = TypeVar('OtpSessionType', bound='OtpSession')

# MARK: Registry -----------------------------------------------------------------------

_reason_subclasses: dict[str, type[OtpSession]] = {}

# MARK: Classes ------------------------------------------------------------------------


@dataclass
class OtpSession(Generic[OptionalAccountType]):
    """
    Make or retrieve an OTP in the user's cookie session.

    This class has an experimental implementation of using a subclass registry to
    retrieve the appropriate subclass given a parameter to the base class. It is unclear
    at the time of this implementation whether this approach has any benefit over the
    caller directly instantiating the appropriate subclass, and is meant to create an
    opportunity to evaluate before this pattern comes up again. The
    :class:`~funnel.models.notification.Notification` model is a prior use case, but
    that one is handled by SQLAlchemy.
    """

    reason: str
    token: str
    otp: str
    user: OptionalAccountType
    email: str | None = None
    phone: str | None = None
    link_token: str | None = None

    # __new__ gets called before __init__ and can replace the class that is created
    def __new__(  # pylint: disable=W0221  # noqa: PYI034
        cls, reason: str, **_kwargs: Any
    ) -> OtpSession:
        """Return a subclass that contains the appropriate methods for given reason."""
        if reason not in _reason_subclasses:
            raise TypeError(f"Unknown OtpSession reason {reason}")

        use_cls = _reason_subclasses[reason]
        return super().__new__(use_cls)  # pyright: ignore[reportArgumentType]

    # __init_subclass__ gets called for ``class Subclass(OtpSession, reason='...'):``
    # and receives `reason` as a kwarg. However, declaring it in the method signature
    # upsets PyLint, so we pop it from kwargs.
    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        """Register a subclass for use by __new__."""
        reason = kwargs.pop('reason', None)
        if not reason:
            raise TypeError("Subclasses of OtpSession must have a `reason` kwarg")
        super().__init_subclass__(*args, **kwargs)
        if reason in _reason_subclasses:
            raise TypeError(f"OtpSession subclass for {reason} already exists")
        _reason_subclasses[reason] = cls
        cls.reason = reason

    @classmethod
    def make(
        cls,
        reason: str,
        user: OptionalAccountType,
        anchor: Anchor | None,
        phone: str | None = None,
        email: str | None = None,
    ) -> Self:
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
        if isinstance(anchor, AccountPhone | PhoneNumber):
            phone = str(anchor)
        if isinstance(anchor, AccountEmail | AccountEmailClaim | EmailAddress):
            email = str(anchor)
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
    def retrieve(cls, reason: str) -> Self:
        """Retrieve an OTP from cache using the token in browser cookie session."""
        otp_token = session.get('otp')
        if not otp_token:
            current_app.logger.info("%s OTP timed out: cookie_expired", reason)
            raise OtpTimeoutError('cookie_expired')
        otp_data = retrieve_cached_token(otp_token)
        if not otp_data:
            current_app.logger.info("%s OTP timed out: cache_expired", reason)
            raise OtpTimeoutError('cache_expired')
        if otp_data['reason'] != reason:
            current_app.logger.info(
                "%s got OTP meant for %s", reason, otp_data['reason']
            )
            raise OtpReasonError(reason)
        user = (
            Account.get(buid=otp_data['user_buid']) if otp_data['user_buid'] else None
        )
        if (
            user is not None
            and current_auth.user is not None
            and user != current_auth.user
        ):
            # The user is replaying someone else's cookie session
            raise OtpUserError('user_mismatch')
        return cls(
            reason=reason,
            token=otp_token,
            otp=otp_data['otp'],
            user=user,  # type: ignore[arg-type]
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

    @cached_property
    def display_phone(self) -> str:
        """Return a display phone number."""
        return mask_phone(self.phone) if self.phone is not None else ''

    @cached_property
    def display_email(self) -> str:
        """Return a display email address."""
        return mask_email(self.email) if self.email is not None else ''

    def compose_sms(self) -> sms.WebOtpTemplate:
        """Compose an OTP SMS message."""
        return sms.WebOtpTemplate(
            otp=self.otp,
            # TODO: Replace helpline_text with a report URL
            helpline_text=f"call {app.config['SITE_SUPPORT_PHONE']}",
            domain=current_app.config['SERVER_NAME'],
        )

    def send_sms(
        self, flash_success: bool = True, flash_failure: bool = True
    ) -> SmsMessage | None:
        """Send an OTP via SMS to a phone number."""
        if not self.phone:
            return None
        template_message = self.compose_sms()
        msg = SmsMessage(phone=self.phone, message=str(template_message))
        try:
            # Now send this
            msg.transactionid = sms.send_sms(
                phone=msg.phone_number, message=template_message
            )
        except TransportRecipientError as exc:
            if flash_failure:
                flash(str(exc), 'error')
            else:
                raise
        except (TransportConnectionError, TransportTransactionError) as exc:
            message = _(
                "Hasgeek cannot send an OTP via SMS to your phone number {number} right"
                " now"
            ).format(number=self.display_phone)
            if flash_failure:
                flash(message, 'error')
            else:
                raise TransportConnectionError(message) from exc
        else:
            # Commit only if an SMS could be sent
            db.session.add(msg)
            db.session.commit()
            if flash_success:
                flash(
                    _(
                        "An OTP has been sent via SMS to your phone number {number}"
                    ).format(number=self.display_phone),
                    'success',
                )
            return msg
        return None

    def send_email(
        self, flash_success: bool = True, flash_failure: bool = True
    ) -> str | None:
        """Send an OTP via email (stub implementation)."""
        raise NotImplementedError("Subclasses must implement ``send_email``")

    def send(self, flash_success: bool = True, flash_failure: bool = True) -> bool:
        """Send an OTP via SMS or email."""
        # Allow 10 OTP sends per 10 minutes per IP address
        validate_rate_limit(
            'otp-send', 'ipaddr/' + (request.remote_addr or ''), 10, 600
        )
        # Allow 3 OTP sends per hour per anchor
        if self.phone is not None:
            try:
                validate_rate_limit(
                    'otp-send', 'phone/' + blake2b160_hex(self.phone), 3, 3600
                )
                success = bool(self.send_sms(flash_success, flash_failure))
                if success:
                    return success
            except TooManyRequests as exc:
                if self.email is None:
                    # There is no fallback to email OTP, so this is a hard rate limit
                    raise exc
            # If an SMS could not be sent (connection error, recipient error, rate
            # limit) but email is available, fallback to sending email
        if self.email is not None:
            validate_rate_limit(
                'otp-send', 'email/' + blake2b160_hex(self.email), 3, 3600
            )
            return bool(self.send_email(flash_success, flash_failure))
        return False

    def mark_transport_active(self) -> None:
        """Mark email and/or phone as active based on user activity."""
        if self.phone and self.email:
            # FIXME: Potential future scenario where email AND phone are sent an OTP.
            # We don't know which is active and it's not safe to assume, so do nothing
            return
        if self.phone:
            try:
                phone_number = PhoneNumber.get(self.phone)
                if phone_number:
                    phone_number.mark_active(sms=True)
            except PhoneNumberBlockedError:
                pass
        elif self.email:
            try:
                email_address = EmailAddress.get(self.email)
                if email_address:
                    email_address.mark_active()
            except EmailAddressBlockedError:
                pass


class OtpSessionForLogin(OtpSession[Account | None], reason='login'):
    """OtpSession variant for login."""

    def send_sms(
        self, flash_success: bool = True, flash_failure: bool = True
    ) -> SmsMessage | None:
        """Send an OTP via SMS to a phone number."""
        if not self.phone:
            return None
        template_message = self.compose_sms()
        msg = SmsMessage(phone=self.phone, message=str(template_message))
        try:
            # Now send this
            msg.transactionid = sms.send_sms(
                phone=msg.phone_number, message=template_message
            )
        except TransportRecipientError as exc:
            if self.user:
                message = _(
                    "Your phone number {number} is not supported for SMS. Use"
                    " password to login"
                ).format(number=self.display_phone)
            else:
                message = _(
                    "Your phone number {number} is not supported for SMS. Use"
                    " an email address to register"
                ).format(number=self.display_phone)
            if flash_failure:
                flash(message, 'error')
            else:
                raise TransportRecipientError(message) from exc
        except (TransportConnectionError, TransportTransactionError) as exc:
            if self.user:
                message = _(
                    "Hasgeek cannot send an OTP via SMS to your phone number {number}"
                    " right now. Use password to login, or try again later"
                ).format(number=self.display_phone)
            else:
                message = _(
                    "Hasgeek cannot send an OTP via SMS to your phone number {number}"
                    " right now. Use an email address to register, or try again later"
                ).format(number=self.display_phone)
            if flash_failure:
                flash(message, 'error')
            else:
                raise TransportConnectionError(message) from exc
        else:
            # Commit only if an SMS could be sent
            db.session.add(msg)
            db.session.commit()
            if flash_success:
                flash(
                    _("An OTP has been sent to your phone number {number}").format(
                        number=self.display_phone
                    ),
                    'success',
                )
            return msg
        return None

    def send_email(
        self, flash_success: bool = True, flash_failure: bool = True
    ) -> str | None:
        """Email a login OTP to the user."""
        if not self.email:
            return None
        fullname = self.user.fullname if self.user is not None else ''
        subject = _("Login OTP {otp}").format(otp=self.otp)
        content = render_template(
            'email_login_otp.html.jinja2',
            fullname=fullname,
            otp=self.otp,
        )
        try:
            result = send_email(subject, [(fullname, self.email)], content)
        except TransportRecipientError as exc:
            if flash_failure:
                flash(str(exc), 'error')
                return None
            raise
        if flash_success:
            flash(
                _("An OTP has been sent to your email address {email}").format(
                    email=self.display_email
                ),
                'success',
            )
        return result


class OtpSessionForSudo(OtpSession[Account], reason='sudo'):
    """OtpSession variant for sudo confirmation."""

    @cached_property
    def display_phone(self) -> str:
        """Reveal phone number when used for sudo."""
        return (
            phonenumbers.format_number(
                phonenumbers.parse(self.phone),
                phonenumbers.PhoneNumberFormat.INTERNATIONAL,
            )
            if self.phone is not None
            else ''
        )

    @cached_property
    def display_email(self) -> str:
        """Reveal email address when used for sudo."""
        return self.email if self.email is not None else ''

    def send_email(
        self, flash_success: bool = True, flash_failure: bool = True
    ) -> str | None:
        """Email a sudo OTP to the user."""
        if not self.email:
            return None
        subject = _("Confirmation OTP {otp}").format(otp=self.otp)
        content = render_template(
            'email_sudo_otp.html.jinja2',
            fullname=self.user.fullname,
            otp=self.otp,
        )
        try:
            result = send_email(subject, [(self.user.fullname, self.email)], content)
        except TransportRecipientError as exc:
            if flash_failure:
                flash(str(exc), 'error')
                return None
            raise
        if flash_success:
            flash(
                _("An OTP has been sent to your email address {email}").format(
                    email=self.display_email
                ),
                'success',
            )
        return result


@dataclass  # Required since this subclass has a __post_init__
class OtpSessionForReset(OtpSession[Account], reason='reset'):
    """OtpSession variant for password reset."""

    def __post_init__(self) -> None:
        """Make link token."""
        self.link_token = token_serializer().dumps(
            {'buid': self.user.buid, 'pw_set_at': str_pw_set_at(self.user)}
        )

    def send_email(
        self, flash_success: bool = True, flash_failure: bool = True
    ) -> str | None:
        """Send OTP and reset link via email."""
        if not self.email:
            return None

        subject = _("Reset your password - OTP {otp}").format(otp=self.otp)
        url = url_for(
            'reset_with_token',
            _external=True,
            token=self.link_token,
            utm_medium='email',
            utm_source='account-reset',
        )
        jsonld = jsonld_view_action(subject, url, _("Reset password"))
        content = render_template(
            'email_account_reset.html.jinja2',
            fullname=self.user.fullname,
            url=url,
            jsonld=jsonld,
            otp=self.otp,
        )
        try:
            result = send_email(subject, [(self.user.fullname, self.email)], content)
        except TransportRecipientError as exc:
            if flash_failure:
                flash(str(exc), 'error')
                return None
            raise
        if flash_success:
            flash(
                _("An OTP has been sent to your email address {email}").format(
                    email=self.display_email
                ),
                'success',
            )
        return result


class OtpSessionForNewPhone(OtpSession[Account], reason='add-phone'):
    """OtpSession variant for adding a phone number."""

    def send_email(
        self,
        flash_success: bool = True,  # noqa: ARG002
        flash_failure: bool = True,  # noqa: ARG002
    ) -> None:
        """OTP for phone does not require email."""
        return


class OtpSessionForNewEmail(OtpSession[Account], reason='add-email'):
    """OtpSession variant for adding an email address."""

    email: str
    user: Account

    @cached_property
    def display_email(self) -> str:
        """Return a display email address."""
        return self.email

    def send_email(
        self, flash_success: bool = True, flash_failure: bool = True
    ) -> str | None:
        """Email an OTP to the user to confirm their email address."""
        subject = _("OTP {otp} to verify your email address").format(otp=self.otp)
        content = render_template(
            'email_add_otp.html.jinja2',
            fullname=self.user.fullname,
            otp=self.otp,
        )
        try:
            result = send_email(subject, [(self.user.fullname, self.email)], content)
        except TransportRecipientError as exc:
            if flash_failure:
                flash(str(exc), 'error')
                return None
            raise
        if flash_success:
            flash(
                _("An OTP has been sent to your email address {email}").format(
                    email=self.display_email
                ),
                'success',
            )
        return result
