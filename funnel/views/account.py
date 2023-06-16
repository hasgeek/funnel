"""Account management views."""

from __future__ import annotations

from string import capwords
from types import SimpleNamespace
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import geoip2.errors
import user_agents
from flask import abort, current_app, flash, redirect, render_template, request, url_for
from markupsafe import Markup, escape

from baseframe import _, forms
from baseframe.forms import render_delete_sqla, render_form, render_message
from coaster.auth import current_auth
from coaster.sqlalchemy import RoleAccessProxy
from coaster.views import ClassView, get_next_url, render_with, route

from .. import app
from ..forms import (
    AccountDeleteForm,
    AccountForm,
    EmailPrimaryForm,
    LogoutForm,
    NewEmailAddressForm,
    NewPhoneForm,
    OtpForm,
    PasswordChangeForm,
    PasswordCreateForm,
    PhonePrimaryForm,
    SavedProjectForm,
    supported_locales,
    timezone_identifiers,
)
from ..models import (
    AccountPasswordNotification,
    AuthClient,
    Organization,
    OrganizationMembership,
    Profile,
    User,
    UserEmail,
    UserEmailClaim,
    UserExternalId,
    UserPhone,
    UserSession,
    db,
    sa,
)
from ..registry import login_registry
from ..signals import user_data_changed
from ..typing import ReturnRenderWith, ReturnResponse, ReturnView
from .decorators import etag_cache_for_user, xhr_only
from .email import send_email_verify_link
from .helpers import (
    app_url_for,
    autoset_timezone_and_locale,
    avatar_color_count,
    render_redirect,
    validate_rate_limit,
)
from .login_session import (
    del_sudo_preference_context,
    login_internal,
    logout_internal,
    requires_login,
    requires_sudo,
)
from .notification import dispatch_notification
from .otp import OtpSession, OtpTimeoutError


@User.views()
def emails_sorted(obj: User) -> List[UserEmail]:
    """Return sorted list of email addresses for account page UI."""
    primary = obj.primary_email
    items = sorted(obj.emails, key=lambda i: (i != primary, i.email or ''))
    return items


@User.views()
def phones_sorted(obj: User) -> List[UserPhone]:
    """Return sorted list of phone numbers for account page UI."""
    primary = obj.primary_phone
    items = sorted(obj.phones, key=lambda i: (i != primary, i.phone or ''))
    return items


@User.views('locale')
def user_locale(obj: User) -> str:
    """Name of user's locale, defaulting to locale identifier."""
    locale = str(obj.locale) if obj.locale is not None else 'en'
    return supported_locales.get(locale, locale)


@User.views('timezone')
def user_timezone(obj: User) -> str:
    """Human-friendly identifier for user's timezone, defaulting to timezone name."""
    return timezone_identifiers.get(
        str(obj.timezone) if obj.timezone else None, obj.timezone
    )


@User.views()
def organizations_as_admin(
    obj: User,
    owner: bool = False,
    limit: Optional[int] = None,
    order_by_grant: bool = False,
) -> List[RoleAccessProxy]:
    """Return organizations that the user is an admin of."""
    if owner:
        orgmems = obj.active_organization_owner_memberships
    else:
        orgmems = obj.active_organization_admin_memberships
    orgmems = orgmems.join(Organization)
    if order_by_grant:
        orgmems = orgmems.order_by(OrganizationMembership.granted_at.desc())
    else:
        orgmems = orgmems.order_by(sa.func.lower(Organization.title))

    if limit is not None:
        orgmems = orgmems.limit(limit)

    orgs = [_om.current_access() for _om in orgmems]
    return orgs


@User.views()
def organizations_as_owner(
    obj: User, limit: Optional[int] = None, order_by_grant: bool = False
) -> List[RoleAccessProxy]:
    """Return organizations that the user is an owner of."""
    return obj.views.organizations_as_admin(
        owner=True, limit=limit, order_by_grant=order_by_grant
    )


@User.views()
def recent_organization_memberships(
    obj: User, recent: int = 3, overflow: int = 4
) -> SimpleNamespace:
    """
    Return recent organizations for the user (by recently edited membership).

    :param recent: Desired count of recent organizations to be listed
    :param overflow: Desired count of recent organizations to be returned as overflow

    :returns: Namespace of ``recent`` (list), ``overflow`` (list) and ``extra_count``
        (int) with the lists containing :class:`OrganizationMembership`` in role access
        proxies

    The items returned under overflow are also included in ``recent_count``, so the
    total count is ``len(recent) + extra_count``.
    """
    orgs = obj.views.organizations_as_admin(
        limit=recent + overflow, order_by_grant=True
    )
    return SimpleNamespace(
        recent=orgs[:recent],
        overflow=orgs[recent : recent + overflow],
        extra_count=max(0, obj.active_organization_admin_memberships.count() - recent),
    )


@User.views('avatar_color_code', cached_property=True)
@Organization.views('avatar_color_code', cached_property=True)
@Profile.views('avatar_color_code', cached_property=True)
def avatar_color_code(obj: Union[User, Organization, Profile]) -> int:
    """Return a colour code for the user's autogenerated avatar image."""
    # Return an int from 0 to avatar_color_count from the initials of the given string
    if obj.title:
        parts = obj.title.split()
        if len(parts) > 1:
            total = ord(parts[0][0]) + ord(parts[-1][0])
        else:
            total = ord(parts[0][0])
    else:
        total = 0
    return total % avatar_color_count


@User.features('not_likely_throwaway', property=True)
def user_not_likely_throwaway(obj: User) -> bool:
    """
    Confirm the user is not likely to be a throwaway account.

    Current criteria: user must have a verified phone number, or user's profile must
    be marked as verified.
    """
    return bool(obj.phone) or (obj.profile is not None and obj.profile.is_verified)


@UserSession.views('user_agent_details')
def user_agent_details(obj: UserSession) -> Dict[str, str]:
    """Return a friendly identifier for the user's browser (HTTP user agent)."""
    ua = user_agents.parse(obj.user_agent)
    if ua.browser.family:
        browser = f"{ua.browser.family or ''} {ua.browser.version_string or ''}".strip()
    else:
        browser = _("Unknown browser")
    if ua.is_pc or ua.device.brand == "Generic":
        device = ''
    elif (
        ua.device.model
        and ua.device.brand
        and ua.device.model.startswith(ua.device.brand)
    ):
        device = ua.device.model
    else:
        device = f"{ua.device.brand or ''} {ua.device.model or ''}".strip()

    if ua.os.family == "Mac OS X":
        if ua.os.version_string.startswith('10.15.'):
            # Safari, Firefox and Chrome report outdated version 10.15.7
            os = "macOS"
        else:
            # Microsoft Edge appears to report the correct version number
            os = f"macOS {ua.os.version_string}"
    else:
        os = f"{ ua.os.family or ''} {ua.os.version_string or ''}".strip()

    if device:
        os_device = f'{device} ({os})'
    elif os:
        os_device = os
    else:
        os_device = _("Unknown device")
    return {'browser': browser, 'os_device': os_device}


@UserSession.views('location')
def user_session_location(obj: UserSession) -> str:
    """Return user's location and ISP as determined from their IP address."""
    if not app.geoip_city or not app.geoip_asn:
        return _("Unknown location")
    try:
        city_lookup = app.geoip_city.city(obj.ipaddr)
        asn_lookup = app.geoip_asn.asn(obj.ipaddr)
    except geoip2.errors.GeoIP2Error:
        return _("Unknown location")

    # ASN is not ISP, but GeoLite2 only has an ASN database. The ISP db is commercial.
    return (
        ((city_lookup.city.name + ", ") if city_lookup.city.name else '')
        + (
            (city_lookup.subdivisions.most_specific.iso_code + ", ")
            if city_lookup.subdivisions.most_specific.iso_code
            else ''
        )
        + ((city_lookup.country.name + "; ") if city_lookup.country.name else '')
        + (asn_lookup.autonomous_system_organization or _("Unknown ISP"))
    )


@UserSession.views('login_service')
def user_session_login_service(obj: UserSession) -> Optional[str]:
    """Return the login provider that was used to create the login session."""
    if obj.login_service == 'otp':
        return _("OTP")
    if obj.login_service in login_registry:
        return login_registry[obj.login_service].title
    return None


@route('/account')
class AccountView(ClassView):
    """Account management views."""

    __decorators__ = [requires_login]

    obj: User
    current_section = 'account'  # needed for showing active tab
    SavedProjectForm = SavedProjectForm

    def loader(self, **kwargs) -> User:
        """Return current user."""
        return current_auth.user

    @route('', endpoint='account')
    @render_with('account.html.jinja2')
    def account(self) -> ReturnRenderWith:
        """View for account management landing page."""
        logout_form = LogoutForm(user=current_auth.user)
        user_has_password = current_auth.user.pw_hash is not None
        primary_email_form = EmailPrimaryForm()
        primary_phone_form = PhonePrimaryForm()
        return {
            'user': current_auth.user.current_access(),
            'user_has_password': user_has_password,
            'authtokens': [
                _at.current_access()
                for _at in current_auth.user.authtokens.join(AuthClient)
                .order_by(AuthClient.trusted.desc(), AuthClient.title)
                .all()
            ],
            'logout_form': logout_form,
            'primary_email_form': primary_email_form,
            'primary_phone_form': primary_phone_form,
            'login_registry': login_registry,
        }

    @route('sudo', endpoint='account_sudo', methods=['GET', 'POST'])
    @requires_sudo
    def sudo(self) -> ReturnResponse:
        """Render a sudo prompt, as needed by :func:`requires_sudo`."""
        del_sudo_preference_context()
        # TODO: get_next_url() should recognise other app domains (for Hasjob).
        return render_redirect(get_next_url())

    @route('saved', endpoint='saved')
    @render_with('account_saved.html.jinja2')
    def saved(self) -> ReturnRenderWith:
        """View for saved projects."""
        return {'saved_projects': current_auth.user.saved_projects}

    @route('menu', endpoint='account_menu')
    @etag_cache_for_user('account_menu', 1, 900)
    @xhr_only(lambda: url_for('account'))
    def menu(self) -> ReturnView:
        """Render account menu."""
        return render_template('account_menu.html.jinja2')

    @route('organizations', endpoint='organizations')
    @render_with('account_organizations.html.jinja2')
    def organizations(self) -> ReturnRenderWith:
        """Render organizations for the user account."""
        return {}

    @route('edit', methods=['GET', 'POST'], endpoint='account_edit')
    def edit(self) -> ReturnView:
        """Edit user's fullname, username, timezone and locale."""
        form = AccountForm(obj=current_auth.user)
        if form.validate_on_submit():
            form.populate_obj(current_auth.user)
            autoset_timezone_and_locale(current_auth.user)

            db.session.commit()
            user_data_changed.send(current_auth.user, changes=['profile'])
            flash(_("Your account has been updated"), category='success')

            return render_redirect(get_next_url(default=url_for('account')))
        return render_form(
            form,
            title=_("Edit account"),
            # Form with id 'form-account_edit' will have username validation
            # in account_formlayout.html.jinja2
            formid='account_edit',
            submit=_("Save changes"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    # FIXME: Don't modify db on GET. Autosubmit via JS and process on POST
    @route('confirm/<email_hash>/<secret>', endpoint='confirm_email')
    def confirm_email(self, email_hash: str, secret: str) -> ReturnView:
        """Confirm an email address using a verification link."""
        try:
            emailclaim = UserEmailClaim.get_by(
                verification_code=secret, email_hash=email_hash
            )
        except ValueError:  # Possible when email_hash is invalid Base58
            abort(404)
        if emailclaim is not None:
            emailclaim.email_address.mark_active()
            if emailclaim.user == current_auth.user:
                existing = UserEmail.get(email=emailclaim.email)
                if existing is not None:
                    claimed_email = emailclaim.email
                    claimed_user = emailclaim.user
                    db.session.delete(emailclaim)
                    db.session.commit()
                    if claimed_user != current_auth.user:
                        return render_message(
                            title=_("Email address already claimed"),
                            message=Markup(
                                _(
                                    "The email address <code>{email}</code> has already"
                                    " been verified by another user"
                                ).format(email=escape(claimed_email))
                            ),
                        )
                    return render_message(
                        title=_("Email address already verified"),
                        message=Markup(
                            _(
                                "Hello, {fullname}! Your email address"
                                " <code>{email}</code> has already been verified"
                            ).format(
                                fullname=escape(claimed_user.fullname),
                                email=escape(claimed_email),
                            )
                        ),
                    )

                useremail = emailclaim.user.add_email(
                    emailclaim.email,
                    primary=not emailclaim.user.emails,
                    private=emailclaim.private,
                )
                for emailclaim in UserEmailClaim.all(useremail.email):
                    db.session.delete(emailclaim)
                db.session.commit()
                user_data_changed.send(current_auth.user, changes=['email'])
                return render_message(
                    title=_("Email address verified"),
                    message=Markup(
                        _(
                            "Hello, {fullname}!"
                            " Your email address <code>{email}</code> has now been"
                            " verified"
                        ).format(
                            fullname=escape(useremail.user.fullname),
                            email=escape(useremail.email),
                        )
                    ),
                )
            return render_message(
                title=_("This was not for you"),
                message=_(
                    "You’ve opened an email verification link that was meant for"
                    " another user. If you are managing multiple accounts, please login"
                    " with the correct account and open the link again"
                ),
                code=403,
            )
        return render_message(
            title=_("Expired confirmation link"),
            message=_(
                "The confirmation link you clicked on is either invalid or has expired"
            ),
            code=404,
        )

    @route('password', methods=['GET', 'POST'], endpoint='change_password')
    def change_password(self) -> ReturnView:
        """Update account password."""
        if not current_auth.user.pw_hash:
            form = PasswordCreateForm(edit_user=current_auth.user)
            title = _("Set password")
        else:
            form = PasswordChangeForm(edit_user=current_auth.user)
            title = _("Change password")
        if form.validate_on_submit():
            current_app.logger.info("Password strength %f", form.password_strength)
            user = current_auth.user
            user.password = form.password.data
            # 1. Log out of the current session
            logout_internal()
            # 2. As a precaution, invalidate all of the user's active sessions
            for user_session in user.active_user_sessions.all():
                user_session.revoke()
            # 3. Create a new session and continue without disrupting user experience
            login_internal(user, login_service='password')
            db.session.commit()
            flash(_("Your new password has been saved"), category='success')
            dispatch_notification(AccountPasswordNotification(document=user))
            # If the user was sent here from login because of a weak password, the next
            # URL will be saved in the session. If so, send the user on their way after
            # setting the password, falling back to the account page if there's nowhere
            # else to send them.
            return render_redirect(
                get_next_url(session=True, default=url_for('account'))
            )
        # Form with id 'form-password-change' will have password strength meter on UI
        return render_form(
            form=form,
            title=title,
            formid='password-change',
            submit=title,
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    @route('email/new', methods=['GET', 'POST'], endpoint='add_email')
    def add_email(self) -> ReturnView:
        """Add a new email address using a confirmation link (legacy, pre-OTP)."""
        form = NewEmailAddressForm(edit_user=current_auth.user)
        if form.validate_on_submit():
            useremail = UserEmailClaim.get_for(
                user=current_auth.user, email=form.email.data
            )
            if useremail is None:
                useremail = UserEmailClaim(
                    user=current_auth.user, email=form.email.data
                )
                db.session.add(useremail)
            send_email_verify_link(useremail)
            db.session.commit()
            flash(_("We sent you an email to confirm your address"), 'success')
            user_data_changed.send(current_auth.user, changes=['email-claim'])
            return render_redirect(url_for('account'))
        return render_form(
            form=form,
            title=_("Add an email address"),
            formid='email_add',
            submit=_("Add email"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    @route('email/makeprimary', methods=['POST'], endpoint='make_email_primary')
    def make_email_primary(self) -> ReturnView:
        """Mark an email address as primary."""
        form = EmailPrimaryForm()
        if form.validate_on_submit():
            useremail = UserEmail.get_for(
                user=current_auth.user, email_hash=form.email_hash.data
            )
            if useremail is not None:
                if useremail.primary:
                    flash(_("This is already your primary email address"), 'info')
                elif useremail.email_address.is_blocked:
                    flash(_("This email address has been blocked from use"), 'error')
                else:
                    current_auth.user.primary_email = useremail
                    db.session.commit()
                    user_data_changed.send(
                        current_auth.user, changes=['email-update-primary']
                    )
                    flash(_("Your primary email address has been updated"), 'success')
            else:
                flash(
                    _("No such email address is linked to this user account"), 'danger'
                )
        else:
            flash(_("Please select an email address"), 'danger')
        return render_redirect(url_for('account'))

    @route('phone/makeprimary', methods=['POST'], endpoint='make_phone_primary')
    def make_phone_primary(self) -> ReturnView:
        """Mark a phone number as primary."""
        form = PhonePrimaryForm()
        if form.validate_on_submit():
            userphone = UserPhone.get_for(
                user=current_auth.user, phone_hash=form.phone_hash.data
            )
            if userphone is not None:
                if userphone.primary:
                    flash(_("This is already your primary phone number"), 'info')
                elif userphone.phone_number.is_blocked:
                    flash(_("This phone number has been blocked from use"), 'error')
                else:
                    current_auth.user.primary_phone = userphone
                    db.session.commit()
                    user_data_changed.send(
                        current_auth.user, changes=['phone-update-primary']
                    )
                    flash(_("Your primary phone number has been updated"), 'success')
            else:
                flash(
                    _("No such phone number is linked to this user account"), 'danger'
                )
        else:
            flash(_("Please select a phone number"), 'danger')
        return render_redirect(url_for('account'))

    @route(
        'email/<email_hash>/remove',
        methods=['GET', 'POST'],
        endpoint='remove_email',
    )
    def remove_email(self, email_hash: str) -> ReturnView:
        """Remove an email address from the user's account."""
        useremail: Union[None, UserEmail, UserEmailClaim]
        try:
            useremail = UserEmail.get_for(user=current_auth.user, email_hash=email_hash)
            if useremail is None:
                useremail = UserEmailClaim.get_for(
                    user=current_auth.user, email_hash=email_hash
                )
            if useremail is None:
                abort(404)
        except ValueError:  # Possible when email_hash is invalid Base58
            abort(404)
        if (
            isinstance(useremail, UserEmail)
            and current_auth.user.verified_contact_count == 1
        ):
            flash(
                _(
                    "Your account requires at least one verified email address or phone"
                    " number"
                ),
                'danger',
            )
            return render_redirect(url_for('account'))
        result = render_delete_sqla(
            useremail,
            db,
            title=_("Confirm removal"),
            message=_("Remove email address {email} from your account?").format(
                email=useremail.email
            ),
            success=_("You have removed your email address {email}").format(
                email=useremail.email
            ),
            next=url_for('account'),
            delete_text=_("Remove"),
        )
        if request.method == 'POST' and result.status_code in (302, 303):
            user_data_changed.send(current_auth.user, changes=['email-delete'])
        return result

    @route(
        'email/<email_hash>/verify',
        methods=['GET', 'POST'],
        endpoint='verify_email',
    )
    def verify_email(self, email_hash: str) -> ReturnView:
        """
        Allow user to resend an email verification link if original is lost.

        This endpoint is only linked to from the account page under the list of email
        addresses pending verification.
        """
        try:
            useremail = UserEmail.get(email_hash=email_hash)
        except ValueError:  # Possible when email_hash is invalid Base58
            abort(404)
        if useremail is not None and useremail.user == current_auth.user:
            # If an email address is already verified (this should not happen unless the
            # user followed a stale link), tell them it's done -- but only if the email
            # address belongs to this user, to prevent this endpoint from being used as
            # a probe for email addresses in the database.
            flash(_("This email address is already verified"), 'danger')
            return render_redirect(url_for('account'))

        # Get the existing email claim that we're resending a verification link for
        try:
            emailclaim = UserEmailClaim.get_for(
                user=current_auth.user, email_hash=email_hash
            )
        except ValueError:  # Possible when email_hash is invalid Base58
            abort(404)
        if emailclaim is None:
            abort(404)
        form = forms.Form()
        if form.validate_on_submit():
            send_email_verify_link(emailclaim)
            db.session.commit()
            flash(_("The verification email has been sent to this address"), 'success')
            return render_redirect(url_for('account'))
        return render_form(
            form=form,
            title=_("Resend the verification email?"),
            message=_("We will resend the verification email to {email}").format(
                email=emailclaim.email
            ),
            formid='email_verify',
            submit=_("Send"),
            template='account_formlayout.html.jinja2',
        )

    @route('phone/new', methods=['GET', 'POST'], endpoint='add_phone')
    def add_phone(self) -> ReturnView:
        """Add a new phone number."""
        form = NewPhoneForm(edit_user=current_auth.user)
        if form.validate_on_submit():
            otp_session = OtpSession.make(
                'add-phone', user=current_auth.user, anchor=None, phone=form.phone.data
            )
            if otp_session.send():
                current_auth.user.main_notification_preferences.by_sms = (
                    form.enable_notifications.data
                )
                return render_redirect(url_for('verify_phone'))
        return render_form(
            form=form,
            title=_("Add a phone number"),
            formid='phone_add',
            submit=_("Verify phone"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    @route('phone/verify', methods=['GET', 'POST'], endpoint='verify_phone')
    def verify_phone(self) -> ReturnView:
        """Verify a phone number with an OTP."""
        try:
            otp_session = OtpSession.retrieve('add-phone')
        except OtpTimeoutError:
            flash(_("This OTP has expired"), category='error')
            return render_redirect(url_for('add_phone'))

        form = OtpForm(valid_otp=otp_session.otp)
        if form.is_submitted():
            # Allow 5 guesses per 60 seconds
            validate_rate_limit('account_phone-otp', otp_session.token, 5, 60)
        if form.validate_on_submit():
            OtpSession.delete()
            if TYPE_CHECKING:
                assert otp_session.phone is not None  # nosec
            if UserPhone.get(otp_session.phone) is None:
                # If there are no existing phone numbers, this will be a primary
                primary = not current_auth.user.phones
                userphone = UserPhone(user=current_auth.user, phone=otp_session.phone)
                userphone.primary = primary
                db.session.add(userphone)
                userphone.phone_number.mark_active(sms=True)
                db.session.commit()
                flash(_("Your phone number has been verified"), 'success')
                user_data_changed.send(current_auth.user, changes=['phone'])
                return render_redirect(
                    get_next_url(session=True, default=url_for('account'))
                )
            flash(
                _("This phone number has already been claimed by another user"),
                'danger',
            )
            return render_redirect(url_for('add_phone'))
        return render_form(
            form=form,
            title=_("Verify phone number"),
            formid='phone_verify',
            submit=_("Verify"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    @route(
        'phone/<phone_hash>/remove', methods=['GET', 'POST'], endpoint='remove_phone'
    )
    @requires_sudo
    def remove_phone(self, phone_hash: str) -> ReturnView:
        """Remove a phone number from the user's account."""
        userphone = UserPhone.get_for(user=current_auth.user, phone_hash=phone_hash)
        if userphone is None:
            abort(404)

        result = render_delete_sqla(
            userphone,
            db,
            title=_("Confirm removal"),
            message=_("Remove phone number {phone} from your account?").format(
                phone=userphone.formatted
            ),
            success=_("You have removed your number {phone}").format(
                phone=userphone.formatted
            ),
            next=url_for('account'),
            delete_text=_("Remove"),
        )
        if request.method == 'POST' and result.status_code in (302, 303):
            user_data_changed.send(current_auth.user, changes=['phone-delete'])
        return result

    # Userid is a path here because obsolete OpenID ids are URLs (both direct and via
    # Google's pre-OAuth2 OpenID protocol)
    @route(
        'extid/<service>/<path:userid>/remove',
        methods=['GET', 'POST'],
        endpoint='remove_extid',
    )
    @requires_sudo
    def remove_extid(self, service: str, userid: str) -> ReturnView:
        """Remove a connected external account."""
        extid = UserExternalId.query.filter_by(
            user=current_auth.user, service=service, userid=userid
        ).one_or_404()
        if extid.service in login_registry:
            service_title = login_registry[extid.service].title
        else:
            service_title = capwords(extid.service)
        return render_delete_sqla(
            extid,
            db,
            title=_("Confirm removal"),
            message=_(
                "Remove {service} account ‘{username}’ from your account?"
            ).format(service=service_title, username=extid.username),
            success=_("You have removed the {service} account ‘{username}’").format(
                service=service_title, username=extid.username
            ),
            next=url_for('account'),
            delete_text=_("Remove"),
        )

    @route('delete', methods=['GET', 'POST'], endpoint='account_delete')
    @requires_sudo
    def delete(self):
        """Delete user account."""
        # Perform sanity checks: can this user account be deleted?
        objection = current_auth.user.views.validate_account_delete()
        if objection:
            return render_message(title=objection.title, message=objection.message)

        # If everything okay, ask user to confirm and then proceed
        form = AccountDeleteForm()
        if form.validate_on_submit():
            # Go ahead, delete
            current_auth.user.do_delete()
            flash(_("Your account has been deleted"), 'success')
            logout_internal()
            db.session.commit()
            return render_template(
                'logout_browser_data.html.jinja2', next=url_for('index')
            )
        return render_form(
            form=form,
            formid='account-delete',
            title=_("You are about to delete your account permanently"),
            submit=("Delete account"),
            ajax=False,
            cancel_url=url_for('account'),
        )


AccountView.init_app(app)


# --- Compatibility routes -------------------------------------------------------------


# Retained for future hasjob integration
# @hasjobapp.route('/account/sudo', endpoint='account_sudo')
def otherapp_account_sudo() -> ReturnResponse:
    """Support the sudo endpoint in other apps."""
    next_url = get_next_url(default=None)
    if next_url:
        # FIXME: Convert relative ``next_url`` into an absolute URL and ensure
        # :meth:`AccountView.sudo` recognises this app's domain
        return redirect(app_url_for(app, 'account_sudo', next=next_url))
    return redirect(app_url_for(app, 'account_sudo'))
