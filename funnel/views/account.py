"""Account management views."""

from __future__ import annotations

import re
from string import capwords
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import user_agents
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from markupsafe import Markup, escape

from baseframe import _, forms
from baseframe.forms import render_delete_sqla, render_form, render_message
from coaster.sqlalchemy import RoleAccessProxy
from coaster.views import ClassView, get_next_url, render_with, route

from .. import app
from ..auth import current_auth
from ..forms import (
    AccountDeleteForm,
    AccountForm,
    EmailOtpForm,
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
from ..geoip import GeoIP2Error, geoip
from ..models import (
    Account,
    AccountEmail,
    AccountEmailClaim,
    AccountExternalId,
    AccountMembership,
    AccountPasswordNotification,
    AccountPhone,
    AuthClient,
    LoginSession,
    Organization,
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
from .login import LogoutBrowserDataTemplate
from .login_session import (
    del_sudo_preference_context,
    login_internal,
    logout_internal,
    requires_login,
    requires_sudo,
)
from .notification import dispatch_notification
from .otp import OtpSession, OtpTimeoutError

# MARK: View registry ------------------------------------------------------------------


@Account.views()
def emails_sorted(obj: Account) -> list[AccountEmail]:
    """Return sorted list of email addresses for account page UI."""
    primary = obj.primary_email
    return sorted(obj.emails, key=lambda i: (i != primary, i.email or ''))


@Account.views()
def phones_sorted(obj: Account) -> list[AccountPhone]:
    """Return sorted list of phone numbers for account page UI."""
    primary = obj.primary_phone
    return sorted(obj.phones, key=lambda i: (i != primary, i.phone or ''))


@Account.views('locale')
def user_locale(obj: Account) -> str:
    """Name of user's locale, defaulting to locale identifier."""
    locale = str(obj.locale) if obj.locale is not None else 'en'
    return supported_locales.get(locale, locale)


@Account.views('timezone')
def user_timezone(obj: Account) -> str:
    """Human-friendly identifier for user's timezone, defaulting to timezone name."""
    timezone = str(u_tz) if (u_tz := obj.timezone) is not None else ''
    return timezone_identifiers.get(timezone, timezone)


@Account.views()
def organizations_as_admin(
    obj: Account,
    owner: bool = False,
    limit: int | None = None,
    order_by_grant: bool = False,
) -> list[RoleAccessProxy[AccountMembership]]:
    """Return organizations that the user is an admin of."""
    if owner:
        orgmems = obj.active_organization_owner_memberships
    else:
        orgmems = obj.active_organization_admin_memberships
    orgmems = orgmems.join(Account, AccountMembership.account)
    if order_by_grant:
        orgmems = orgmems.order_by(AccountMembership.granted_at.desc())
    else:
        orgmems = orgmems.order_by(sa.func.lower(Organization.title))

    if limit is not None:
        orgmems = orgmems.limit(limit)

    return [_om.current_access() for _om in orgmems]


@Account.views()
def organizations_as_owner(
    obj: Account, limit: int | None = None, order_by_grant: bool = False
) -> list[RoleAccessProxy[Account]]:
    """Return organizations that the user is an owner of."""
    return obj.views.organizations_as_admin(
        owner=True, limit=limit, order_by_grant=order_by_grant
    )


@Account.views()
def recent_organization_memberships(
    obj: Account, recent: int = 3, overflow: int = 4
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


@Account.views(cached_property=True)
def organizations_as_member(obj: Account) -> list[RoleAccessProxy[Account]]:
    """Return organizations that the user has a membership in."""
    return [
        acc.access_for(actor=obj, datasets=('primary', 'related'))
        for acc in Account.query.filter(
            Account.name_in(app.config['FEATURED_ACCOUNTS'])
        ).all()
        if 'member' in acc.roles_for(obj)
    ]


@Account.views('avatar_color_code', cached_property=True)
def avatar_color_code(obj: Account) -> int:
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


@Account.features('not_likely_throwaway', property=True)
def user_not_likely_throwaway(obj: Account) -> bool:
    """
    Confirm the user is not likely to be a throwaway account.

    Current criteria: user must have a verified phone number, or the account must be
    marked as verified.
    """
    return obj.is_verified or bool(obj.phone)


_quoted_str_re = re.compile('"(.*?)"')
_quoted_ua_re = re.compile(r'"(.*?)"\s*;\s*v\s*=\s*"(.*?)",?\s*')
_fake_ua_re = re.compile(
    r'\s*.?Not.A.Brand.?\s*|\s*.?Not.Your.Browser.?\s*', re.IGNORECASE
)


def get_ch_ua_string(ch_ua_str: str | None) -> str | None:
    """Parse Sec-CH-UA-* single value header."""
    if not ch_ua_str:
        return None
    match = _quoted_str_re.match(ch_ua_str)
    if match:
        return match[1] or None
    return None


def get_ch_ua(ch_ua: str | None) -> tuple[str, str] | None:
    """Parse Sec-CH-UA or Sec-CH-UA-Full-Version-List header."""
    if not ch_ua:
        return None
    results = [
        (browser, version)
        for browser, version in _quoted_ua_re.findall(ch_ua)
        if not _fake_ua_re.match(browser)
    ]
    if len(results) > 1:
        # Find and remove Chromium from results as it's duplicated
        results = [
            (browser, version)
            for browser, version in results
            if browser.lower() != 'chromium'
        ]
    if results:
        return results[0]
    return None


@LoginSession.views('user_agent_details')
def user_agent_details(obj: LoginSession) -> dict[str, Any]:
    """Return a friendly identifier for the user's browser (HTTP user agent)."""
    mobile: bool | None = None
    browser: str = ''
    device: str = ''
    platform: str = ''

    # Process client hints if available
    client_hints = obj.user_agent_client_hints
    if client_hints:
        match client_hints.get('sec-ch-ua-mobile'):
            case '?0':
                mobile = False
            case '?1':
                mobile = True
        device = get_ch_ua_string(client_hints.get('sec-ch-ua-model')) or ''
        platform = get_ch_ua_string(client_hints.get('sec-ch-ua-platform')) or ''
        platform_version = get_ch_ua_string(
            client_hints.get('sec-ch-ua-platform-version')
        )
        if platform_version:
            if platform == "Windows":
                # Windows platform version numbers are API versions, so remap
                # https://learn.microsoft.com/en-us/microsoft-edge/web-platform/how-to-detect-win11#detecting-specific-windows-versions
                windows_api_version: str | int
                windows_api_version = platform_version.split('.')[0]
                platform_version = ''
                if windows_api_version.isdigit():
                    windows_api_version = int(windows_api_version)
                    if windows_api_version == 0:
                        platform_version = '7/8/8.1'
                    elif 1 <= int(windows_api_version) <= 10:
                        platform_version = '10'
                    elif windows_api_version >= 13:
                        platform_version = '11'
            platform = f'{platform} {platform_version}'.strip()
        browser_version = get_ch_ua(
            client_hints.get('sec-ch-ua-full-version-list')
            or client_hints.get('sec-ch-ua')
        )
        if browser_version:
            browser = f'{browser_version[0]} {browser_version[1]}'.strip()

    ua = user_agents.parse(obj.user_agent)
    if mobile is None:
        mobile = ua.is_mobile
    if not browser:
        if ua.browser.family:
            browser = (
                f"{ua.browser.family or ''} {ua.browser.version_string or ''}".strip()
            )
        else:
            browser = _("Unknown browser")
    if not device:
        if ua.is_pc or (
            ua.device.brand
            and (
                ua.device.brand == "Generic"
                or ua.device.brand.startswith("Generic_Android")
            )
        ):
            device = ''
        elif (
            ua.device.model
            and ua.device.brand
            and ua.device.model.startswith(ua.device.brand)
        ):
            device = ua.device.model
        else:
            device = f"{ua.device.brand or ''} {ua.device.model or ''}".strip()

    if not platform:
        if ua.os.family == "Mac OS X":
            if (
                ua.os.version_string.startswith('10.15.')
                or ua.os.version_string == '10.15'
            ):
                # Safari, Firefox and Chrome report outdated version 10.15.7
                platform = "macOS"
            else:
                # Microsoft Edge appears to report the correct version number
                platform = f"macOS {ua.os.version_string}"
        elif ua.os.family == "Android" and ua.os.version_string == "10":
            # Android > 10 is usually reported as 10
            platform = "Android"
        elif ua.os.family == "Windows" and ua.os.version_string == "10":
            # Windows 11 is reported as Windows 10
            platform = "Windows"
        else:
            platform = f"{ ua.os.family or ''} {ua.os.version_string or ''}".strip()

    if device:
        device_platform = f'{device} ({platform})'
    elif platform:
        device_platform = platform
    else:
        device_platform = _("Unknown device")
    return {'browser': browser, 'device_platform': device_platform, 'mobile': mobile}


@LoginSession.views('location')
def login_session_location(obj: LoginSession) -> str:
    """Return user's location and ISP as determined from their IP address."""
    if obj.ipaddr == '127.0.0.1':
        return _("This device")
    if not geoip:
        return _("Unknown location")
    try:
        city_lookup = geoip.city(obj.ipaddr)
        asn_lookup = geoip.asn(obj.ipaddr)
    except GeoIP2Error:
        return _("Unknown location")

    # ASN is not ISP, but GeoLite2 only has an ASN database. The ISP db is commercial.
    if city_lookup:
        result = (
            ((city_lookup.city.name + ", ") if city_lookup.city.name else '')
            + (
                (city_lookup.subdivisions.most_specific.iso_code + ", ")
                if city_lookup.subdivisions.most_specific.iso_code
                else ''
            )
            + ((city_lookup.country.name + "; ") if city_lookup.country.name else '')
        )
    else:
        result = ''
    if asn_lookup:
        result += asn_lookup.autonomous_system_organization or _("Unknown ISP")
    return result


@LoginSession.views('login_service')
def login_session_service(obj: LoginSession) -> str | None:
    """Return the login provider that was used to create the login session."""
    if obj.login_service == 'otp':
        return _("OTP")
    if obj.login_service in login_registry:
        return login_registry[obj.login_service].title
    return None


# MARK: Views --------------------------------------------------------------------------


@route('/account', init_app=app)
class AccountView(ClassView):
    """Account management views."""

    __decorators__ = [requires_login]

    current_section = 'account'  # needed for showing active tab
    SavedProjectForm = SavedProjectForm

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
            autoset_timezone_and_locale()

            db.session.commit()
            user_data_changed.send(current_auth.user, changes=['profile'])
            flash(_("Your account has been updated"), category='success')

            return render_redirect(get_next_url(default=url_for('account')))
        return render_form(
            form,
            title=_("Your account"),
            # Form with id 'form-account_edit' will have username validation
            # in account_formlayout.html.jinja2
            formid='account_edit',
            submit=_("Save changes"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    # FIXME: Don't modify db on GET. Autosubmit via JS and process on POST
    @route('confirm/<email_hash>/<secret>', endpoint='confirm_email_legacy')
    def confirm_email_legacy(self, email_hash: str, secret: str) -> ReturnView:
        """Confirm an email address using a legacy verification link."""
        try:
            emailclaim = AccountEmailClaim.get_by(
                verification_code=secret, email_hash=email_hash
            )
        except ValueError:  # Possible when email_hash is invalid Base58
            abort(404)
        if emailclaim is not None:
            emailclaim.email_address.mark_active()
            if emailclaim.account == current_auth.user:
                existing = AccountEmail.get(email=emailclaim.email)
                if existing is not None:
                    claimed_email = emailclaim.email
                    claimed_user = emailclaim.account
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

                accountemail = emailclaim.account.add_email(
                    emailclaim.email,
                    primary=not emailclaim.account.emails,
                    private=emailclaim.private,
                )
                for emailclaim in AccountEmailClaim.all(accountemail.email):
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
                            fullname=escape(accountemail.account.title),
                            email=escape(accountemail.email),
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
            for login_session in user.active_login_sessions.all():
                login_session.revoke()
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
        """Add a new email address using an OTP."""
        form = NewEmailAddressForm(edit_user=current_auth.user)
        if form.validate_on_submit():
            otp_session = OtpSession.make(
                'add-email', user=current_auth.user, anchor=None, email=form.email.data
            )
            if otp_session.send():
                current_auth.user.main_notification_preferences.by_email = (
                    form.enable_notifications.data
                )
                return render_redirect(url_for('verify_email'))
        return render_form(
            form=form,
            title=_("Add an email address"),
            formid='email_add',
            submit=_("Verify email"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    @route('email/verify', methods=['GET', 'POST'], endpoint='verify_email')
    def verify_email(self) -> ReturnView:
        """Verify an email address with an OTP."""
        try:
            otp_session = OtpSession.retrieve('add-email')
        except OtpTimeoutError:
            flash(_("This OTP has expired"), category='error')
            return render_redirect(url_for('add_email'))

        form = EmailOtpForm(valid_otp=otp_session.otp)
        if form.is_submitted():
            # Allow 5 guesses per 60 seconds
            validate_rate_limit('account_email-otp', otp_session.token, 5, 60)
        if form.validate_on_submit():
            OtpSession.delete()
            if TYPE_CHECKING:
                assert otp_session.email is not None
            existing = AccountEmail.get(otp_session.email)
            if existing is None:
                # This email address is available to claim. If there are no other email
                # addresses in this account, this will be a primary
                primary = not current_auth.user.emails
                useremail = AccountEmail(
                    account=current_auth.user, email=otp_session.email
                )
                useremail.primary = primary
                db.session.add(useremail)
                useremail.email_address.mark_active()
                db.session.commit()
                flash(_("Your email address has been verified"), 'success')
                user_data_changed.send(current_auth.user, changes=['email'])
                return render_redirect(
                    get_next_url(session=True, default=url_for('account'))
                )
            # Already linked to another account, but we have verified the ownership, so
            # proceed to merge account flow here
            session['merge_buid'] = existing.user.buid
            return render_redirect(url_for('account_merge'))
        return render_form(
            form=form,
            title=_("Verify email address"),
            formid='email_verify',
            submit=_("Verify"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    @route('email/makeprimary', methods=['POST'], endpoint='make_email_primary')
    def make_email_primary(self) -> ReturnView:
        """Mark an email address as primary."""
        form = EmailPrimaryForm()
        if form.validate_on_submit():
            accountemail = AccountEmail.get_for(
                account=current_auth.user, email_hash=form.email_hash.data
            )
            if accountemail is not None:
                if accountemail.primary:
                    flash(_("This is already your primary email address"), 'info')
                elif accountemail.email_address.is_blocked:
                    flash(_("This email address has been blocked from use"), 'error')
                else:
                    current_auth.user.primary_email = accountemail
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
            accountphone = AccountPhone.get_for(
                account=current_auth.user, phone_hash=form.phone_hash.data
            )
            if accountphone is not None:
                if accountphone.primary:
                    flash(_("This is already your primary phone number"), 'info')
                elif accountphone.phone_number.is_blocked:
                    flash(_("This phone number has been blocked from use"), 'error')
                else:
                    current_auth.user.primary_phone = accountphone
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
        accountemail: AccountEmail | AccountEmailClaim | None
        try:
            accountemail = AccountEmail.get_for(
                account=current_auth.user, email_hash=email_hash
            )
            if accountemail is None:
                accountemail = AccountEmailClaim.get_for(
                    account=current_auth.user, email_hash=email_hash
                )
            if accountemail is None:
                abort(404)
        except ValueError:  # Possible when email_hash is invalid Base58
            abort(404)
        if (
            isinstance(accountemail, AccountEmail)
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
            accountemail,
            db,
            title=_("Confirm removal"),
            message=_("Remove email address {email} from your account?").format(
                email=accountemail.email
            ),
            success=_("You have removed your email address {email}").format(
                email=accountemail.email
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
        endpoint='verify_email_legacy',
    )
    def verify_email_legacy(self, email_hash: str) -> ReturnView:
        """
        Allow user to resend an email verification link if original is lost.

        This endpoint is only linked to from the account page under the list of email
        addresses pending verification.
        """
        try:
            accountemail = AccountEmail.get(email_hash=email_hash)
        except ValueError:  # Possible when email_hash is invalid Base58
            abort(404)
        if accountemail is not None and accountemail.account == current_auth.user:
            # If an email address is already verified (this should not happen unless the
            # user followed a stale link), tell them it's done -- but only if the email
            # address belongs to this user, to prevent this endpoint from being used as
            # a probe for email addresses in the database.
            flash(_("This email address is already verified"), 'danger')
            return render_redirect(url_for('account'))

        # Get the existing email claim that we're resending a verification link for
        try:
            emailclaim = AccountEmailClaim.get_for(
                account=current_auth.user, email_hash=email_hash
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
                assert otp_session.phone is not None
            existing = AccountPhone.get(otp_session.phone)
            if existing is None:
                # This phone number is available to claim. If there are no other
                # phone numbers in this account, this will be a primary
                primary = not current_auth.user.phones
                accountphone = AccountPhone(
                    account=current_auth.user, phone=otp_session.phone
                )
                accountphone.primary = primary
                db.session.add(accountphone)
                accountphone.phone_number.mark_active(sms=True)
                db.session.commit()
                flash(_("Your phone number has been verified"), 'success')
                user_data_changed.send(current_auth.user, changes=['phone'])
                return render_redirect(
                    get_next_url(session=True, default=url_for('account'))
                )
            # Already linked to another user, but we have verified the ownership, so
            # proceed to merge account flow here
            session['merge_buid'] = existing.user.buid
            return render_redirect(url_for('account_merge'))
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
        accountphone = AccountPhone.get_for(
            account=current_auth.user, phone_hash=phone_hash
        )
        if accountphone is None:
            abort(404)

        result = render_delete_sqla(
            accountphone,
            db,
            title=_("Confirm removal"),
            message=_("Remove phone number {phone} from your account?").format(
                phone=accountphone.formatted
            ),
            success=_("You have removed your number {phone}").format(
                phone=accountphone.formatted
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
        extid = AccountExternalId.query.filter_by(
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
    def delete(self) -> ReturnView:
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
            return LogoutBrowserDataTemplate(next=url_for('index')).render_template()
        return render_form(
            form=form,
            formid='account-delete',
            title=_("You are about to delete your account permanently"),
            submit=("Delete account"),
            ajax=False,
            cancel_url=url_for('account'),
        )


# MARK: Compatibility routes -----------------------------------------------------------


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
