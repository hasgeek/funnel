from datetime import datetime, timedelta
from hashlib import blake2b
from types import SimpleNamespace
from typing import List, Optional, Union

from flask import (
    Markup,
    abort,
    current_app,
    escape,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

import geoip2.errors
import user_agents

from baseframe import _, cache
from baseframe.forms import (
    render_delete_sqla,
    render_form,
    render_message,
    render_redirect,
)
from coaster.auth import current_auth
from coaster.sqlalchemy import RoleAccessProxy
from coaster.views import ClassView, get_next_url, render_with, route

from .. import app
from ..forms import (
    AccountForm,
    EmailPrimaryForm,
    LogoutForm,
    NewEmailAddressForm,
    NewPhoneForm,
    PasswordChangeForm,
    PasswordCreateForm,
    PasswordPolicyForm,
    PhonePrimaryForm,
    SavedProjectForm,
    UsernameAvailableForm,
    VerifyEmailForm,
    VerifyPhoneForm,
    supported_locales,
    timezone_identifiers,
)
from ..models import (
    AccountPasswordNotification,
    AuthClient,
    Organization,
    OrganizationMembership,
    SMSMessage,
    User,
    UserEmail,
    UserEmailClaim,
    UserExternalId,
    UserPhone,
    UserPhoneClaim,
    UserSession,
    db,
    password_policy,
)
from ..registry import login_registry
from ..signals import user_data_changed
from ..transports import TransportConnectionError, TransportRecipientError, sms
from ..typing import ReturnRenderWith, ReturnResponse, ReturnView
from .email import send_email_verify_link
from .helpers import (
    app_url_for,
    autoset_timezone_and_locale,
    progressive_rate_limit_validator,
    validate_rate_limit,
)
from .login_session import (
    login_internal,
    logout_internal,
    requires_login,
    requires_sudo,
)
from .notification import dispatch_notification


@User.views()
def emails_sorted(obj):
    """Return sorted list of email addresses for account page UI."""
    primary = obj.primary_email
    items = sorted(obj.emails, key=lambda i: (i != primary, i.email))
    return items


@User.views()
def phones_sorted(obj):
    """Return sorted list of phone numbers for account page UI."""
    primary = obj.primary_phone
    items = sorted(obj.phones, key=lambda i: (i != primary, i.phone))
    return items


@User.views('locale')
def user_locale(obj):
    """Name of user's locale, defaulting to locale identifier."""
    return supported_locales.get(str(obj.locale) if obj.locale else None, obj.locale)


@User.views('timezone')
def user_timezone(obj):
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
    if owner:
        orgmems = obj.active_organization_owner_memberships
    else:
        orgmems = obj.active_organization_admin_memberships
    orgmems = orgmems.join(Organization)
    if order_by_grant:
        orgmems = orgmems.order_by(OrganizationMembership.granted_at.desc())
    else:
        orgmems = orgmems.order_by(db.func.lower(Organization.title))

    if limit is not None:
        orgmems = orgmems.limit(limit)

    orgs = [_om.current_access() for _om in orgmems]
    return orgs


@User.views()
def organizations_as_owner(
    obj: User, limit: Optional[int] = None, order_by_grant: bool = False
) -> List[RoleAccessProxy]:
    return obj.views.organizations_as_admin(
        owner=True, limit=limit, order_by_grant=order_by_grant
    )


@User.views()
def recent_organization_memberships(
    obj: User, recent: int = 3, overflow: int = 4
) -> SimpleNamespace:
    orgs = obj.views.organizations_as_admin(
        limit=recent + overflow, order_by_grant=True
    )
    return SimpleNamespace(
        recent=orgs[:recent],
        overflow=orgs[recent : recent + overflow],
        extra_count=max(
            0, obj.active_organization_admin_memberships.count() - recent - overflow
        ),
    )


@UserSession.views('user_agent_details')
def user_agent_details(obj):
    ua = user_agents.parse(obj.user_agent)
    return {
        'browser': (ua.browser.family + ' ' + ua.browser.version_string)
        if ua.browser.family
        else _("Unknown browser"),
        'os_device': (
            (_("PC") + ' ')
            if ua.is_pc
            else str(ua.device.brand or '') + ' ' + str(ua.device.model or '') + ' '
        )
        + ' ('
        + (str(ua.os.family) + ' ' + str(ua.os.version_string)).strip()
        + ')',
    }


@UserSession.views('location')
def user_session_location(obj):
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
def user_session_login_service(obj):
    if obj.login_service in login_registry:
        return login_registry[obj.login_service].title


@app.route('/api/1/account/password_policy', methods=['POST'])
@render_with(json=True)
def password_policy_check():
    policy_form = PasswordPolicyForm()
    policy_form.form_nonce.data = policy_form.form_nonce.default()

    if policy_form.validate_on_submit():
        user_inputs = []

        if current_auth.user:
            if current_auth.user.fullname:
                user_inputs.append(current_auth.user.fullname)

            for useremail in current_auth.user.emails:
                user_inputs.append(str(useremail))
            for emailclaim in current_auth.user.emailclaims:
                user_inputs.append(str(emailclaim))

            for userphone in current_auth.user.phones:
                user_inputs.append(str(userphone))
            for phoneclaim in current_auth.user.phoneclaims:
                user_inputs.append(str(phoneclaim))

        tested_password = password_policy.test_password(
            policy_form.password.data,
            user_inputs=user_inputs if user_inputs else None,
        )
        return {
            'status': 'ok',
            'result': {
                # zxcvbn scores are 0-4, frond-end expects strength value from 0.0-1.0.
                # Keeping the backend score to backend will let us switch strength
                # calculations later on.
                'strength': tested_password['score'] / 4.0,
                'is_weak': tested_password['is_weak'],
                'strength_verbose': (
                    _("Weak password")
                    if tested_password['is_weak']
                    else _("Strong password")
                ),
                'warning': tested_password['warning'],
                'suggestions': tested_password['suggestions'],
            },
        }
    return {
        'status': 'error',
        'error_code': 'policy_form_error',
        'error_description': _("Something went wrong. Please reload and try again"),
        'error_details': policy_form.errors,
    }, 422


@app.route('/api/1/account/username_available', methods=['POST'])
@render_with(json=True)
def account_username_availability():
    form = UsernameAvailableForm(edit_user=current_auth.user)
    del form.form_nonce

    # This view does not use the simpler ``if form.validate()`` construct because
    # we need to insert the rate limiter _between_ the other validators. This will be
    # simpler if :func:`validate_rate_limit` is repositioned as a form validator rather
    # than a view validator.
    form_validate = form.validate()

    if not form_validate:
        # If no username is supplied, return a 422 Unprocessable Entity
        if not form.username.data:
            return {
                'status': 'error',
                'error': 'username_required',
            }, 422

        # Require CSRF validation to prevent this endpoint from being used by a scraper.
        # Field will be missing in a test environment, so use hasattr
        if hasattr(form, 'csrf_token') and form.csrf_token.errors:
            return {
                'status': 'error',
                'error': 'csrf_token',
            }, 422

    # Allow user or source IP to check for up to 20 usernames every 10 minutes (600s)
    validate_rate_limit(
        'account_username_available',
        current_auth.actor.uuid_b58 if current_auth.actor else request.remote_addr,
        # 20 username candidates
        20,
        # per every 10 minutes (600s)
        600,
        # Use a token and validator to count progressive typing and backspacing as a
        # single rate-limited call
        token=form.username.data,
        validator=progressive_rate_limit_validator,
    )

    # Validate form
    if form_validate:
        # All okay? Username is available
        return {'status': 'ok'}

    # If username is supplied but invalid, return HTTP 200 with an error message.
    # 400/422 is the wrong code as the request is valid and the error is app content
    return {
        'status': 'error',
        'error': 'validation_failure',
        # Use the first known error as the description
        'error_description': (
            str(form.username.errors[0])
            if form.username.errors
            else str(list(form.errors.values())[0][0])
        ),
    }, 200


@route('/account')
class AccountView(ClassView):
    """Account management views."""

    __decorators__ = [requires_login]

    current_section = 'account'  # needed for showing active tab
    SavedProjectForm = SavedProjectForm

    def loader(self, **kwargs) -> User:
        return current_auth.user

    @route('', endpoint='account')
    @render_with('account.html.jinja2')
    def account(self) -> ReturnRenderWith:
        logout_form = LogoutForm(user=current_auth.user)
        primary_email_form = EmailPrimaryForm()
        primary_phone_form = PhonePrimaryForm()
        return {
            'user': current_auth.user.current_access(),
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
        return redirect(get_next_url(), code=303)

    @route('saved', endpoint='saved')
    @render_with('account_saved.html.jinja2')
    def saved(self) -> ReturnRenderWith:
        return {'saved_projects': current_auth.user.saved_projects}

    @route('menu', endpoint='account_menu')
    def menu(self):
        """Render account menu."""
        # This is an experimental implementation of caching with ETag. It needs to be
        # generalized into a view decorator
        max_age = 900  # 900 seconds = 15 minutes
        template_version = 1  # Update this number when the template changes
        cache_key = f'account_menu/{template_version}/{current_auth.user.uuid_b64}'
        cache_data = cache.get(cache_key)
        rendered_template = None
        if cache_data:
            try:
                rendered_template = cache_data['rendered_template']
                chash = cache_data['blake2b']
                etag = cache_data['etag']
                last_modified = cache_data['last_modified']
                # TODO: Decorator version's ETag hash should be based on request Accept
                # headers as well, as that changes the response. Or, all headers
                # that are in `response.vary`, although some values for that header are
                # set in `after_request` processors and won't be available here.
                if (
                    etag
                    != blake2b(
                        f'{current_auth.user.uuid_b64}/{chash}'.encode()
                    ).hexdigest()
                ):
                    rendered_template = None
            except KeyError:
                # If any of `rendered_template`, `chash`, `etag` or `last_modified` are
                # missing, discard the cache
                rendered_template = None
        if rendered_template is None:
            rendered_template = render_template('account_menu.html.jinja2')
            chash = blake2b(rendered_template.encode()).hexdigest()
            etag = blake2b(f'{current_auth.user.uuid_b64}/{chash}'.encode()).hexdigest()
            last_modified = datetime.utcnow()
            cache.set(
                cache_key,
                {
                    'rendered_template': rendered_template,
                    'blake2b': chash,
                    'etag': etag,
                    'last_modified': last_modified,
                },
                timeout=max_age,
            )
        response = make_response(rendered_template)
        response.set_etag(etag)
        response.last_modified = last_modified
        response.cache_control.max_age = max_age
        response.expires = (response.last_modified or datetime.utcnow()) + timedelta(
            seconds=max_age
        )
        return response.make_conditional(request)

    @route('organizations', endpoint='organizations')
    @render_with('account_organizations.html.jinja2')
    def organizations(self) -> ReturnRenderWith:
        return {}

    @route(
        'edit',
        methods=['GET', 'POST'],
        defaults={'newprofile': False},
        endpoint='account_edit',
    )
    @route(
        'new',
        methods=['GET', 'POST'],
        defaults={'newprofile': True},
        endpoint='account_new',
    )
    def account_edit(self, newprofile: bool = False) -> ReturnView:
        form = AccountForm(obj=current_auth.user)
        form.edit_user = current_auth.user
        if current_auth.user.email or newprofile is False:
            del form.email

        if form.validate_on_submit():
            # Can't auto-populate here because user.email is read-only
            current_auth.user.fullname = form.fullname.data
            current_auth.user.username = form.username.data
            current_auth.user.timezone = form.timezone.data
            current_auth.user.auto_timezone = form.auto_timezone.data
            current_auth.user.locale = form.locale.data
            current_auth.user.auto_locale = form.auto_locale.data
            autoset_timezone_and_locale(current_auth.user)

            if newprofile and not current_auth.user.email:
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
                user_data_changed.send(
                    current_auth.user, changes=['profile', 'email-claim']
                )
                flash(
                    _(
                        "Your profile has been updated. We sent you an email to confirm"
                        " your address"
                    ),
                    category='success',
                )
            else:
                db.session.commit()
                user_data_changed.send(current_auth.user, changes=['profile'])
                flash(_("Your profile has been updated"), category='success')

            if newprofile:
                return render_redirect(get_next_url(), code=303)
            return render_redirect(url_for('account'), code=303)
        if newprofile:
            return render_form(
                form,
                title=_("Update account"),
                # Form with id 'form-account_new' will have username validation
                # in account_formlayout.html.jinja2
                formid='account_new',
                submit=_("Continue"),
                message=Markup(
                    _(
                        "Hello, {fullname}. Please spare a minute to fill out your"
                        " account"
                    ).format(fullname=escape(current_auth.user.fullname))
                ),
                ajax=False,
                template='account_formlayout.html.jinja2',
            )
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
                    type=emailclaim.type,
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
                get_next_url(session=True, default=url_for('account')), code=303
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
        form = NewEmailAddressForm()
        if form.validate_on_submit():
            useremail = UserEmailClaim.get_for(
                user=current_auth.user, email=form.email.data
            )
            if useremail is None:
                useremail = UserEmailClaim(
                    user=current_auth.user, email=form.email.data, type=form.type.data
                )
                db.session.add(useremail)
            send_email_verify_link(useremail)
            db.session.commit()
            flash(_("We sent you an email to confirm your address"), 'success')
            user_data_changed.send(current_auth.user, changes=['email-claim'])
            return render_redirect(url_for('account'), code=303)
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
        form = EmailPrimaryForm()
        if form.validate_on_submit():
            useremail = UserEmail.get_for(user=current_auth.user, email=form.email.data)
            if useremail is not None:
                if useremail.primary:
                    flash(_("This is already your primary email address"), 'info')
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
        return render_redirect(url_for('account'), code=303)

    @route('phone/makeprimary', methods=['POST'], endpoint='make_phone_primary')
    def make_phone_primary(self) -> ReturnView:
        form = PhonePrimaryForm()
        if form.validate_on_submit():
            userphone = UserPhone.get_for(user=current_auth.user, phone=form.phone.data)
            if userphone is not None:
                if userphone.primary:
                    flash(_("This is already your primary phone number"), 'info')
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
        return render_redirect(url_for('account'), code=303)

    @route(
        'email/<email_hash>/remove',
        methods=['GET', 'POST'],
        endpoint='remove_email',
    )
    def remove_email(self, email_hash: str) -> ReturnView:
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
            return render_redirect(url_for('account'), code=303)
        if request.method == 'POST':
            # FIXME: Confirm validation success
            user_data_changed.send(current_auth.user, changes=['email-delete'])
        return render_delete_sqla(
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
            return render_redirect(url_for('account'), code=303)

        # Get the existing email claim that we're resending a verification link for
        try:
            emailclaim = UserEmailClaim.get_for(
                user=current_auth.user, email_hash=email_hash
            )
        except ValueError:  # Possible when email_hash is invalid Base58
            abort(404)
        if emailclaim is None:
            abort(404)
        verify_form = VerifyEmailForm()
        if verify_form.validate_on_submit():
            send_email_verify_link(emailclaim)
            db.session.commit()
            flash(_("The verification email has been sent to this address"), 'success')
            return render_redirect(url_for('account'), code=303)
        return render_form(
            form=verify_form,
            title=_("Resend the verification email?"),
            message=_(
                "We will resend the verification email to {email}".format(
                    email=emailclaim.email
                )
            ),
            formid="email_verify",
            submit=_("Send"),
            template='account_formlayout.html.jinja2',
        )

    @route('phone/new', methods=['GET', 'POST'], endpoint='add_phone')
    def add_phone(self) -> ReturnView:
        form = NewPhoneForm()
        if form.validate_on_submit():
            userphone = UserPhoneClaim.get_for(
                user=current_auth.user, phone=form.phone.data
            )
            if userphone is None:
                userphone = UserPhoneClaim(
                    user=current_auth.user, phone=form.phone.data
                )
                db.session.add(userphone)
            current_auth.user.main_notification_preferences.by_sms = (
                form.enable_notifications.data
            )
            msg = SMSMessage(
                phone_number=userphone.phone,
                message=current_app.config['SMS_VERIFICATION_TEMPLATE'].format(
                    code=userphone.verification_code
                ),
            )
            try:
                # Now send this
                msg.transactionid = sms.send(msg.phone_number, msg.message)
            except TransportRecipientError as e:
                flash(str(e), 'error')
            except TransportConnectionError:
                flash(_("Unable to send a message right now. Try again later"), 'error')
            else:
                # Commit only if an SMS could be sent
                db.session.add(msg)
                db.session.commit()
                flash(
                    _("A verification code has been sent to your phone number"),
                    'success',
                )
                user_data_changed.send(current_auth.user, changes=['phone-claim'])
                return render_redirect(
                    url_for('verify_phone', number=userphone.phone), code=303
                )
        return render_form(
            form=form,
            title=_("Add a phone number"),
            formid='phone_add',
            submit=_("Verify phone"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    @route('phone/<number>/remove', methods=['GET', 'POST'], endpoint='remove_phone')
    @requires_sudo
    def remove_phone(self, number: str) -> ReturnView:
        userphone: Union[None, UserPhone, UserPhoneClaim]
        userphone = UserPhone.get(phone=number)
        if userphone is None or userphone.user != current_auth.user:
            userphone = UserPhoneClaim.get_for(user=current_auth.user, phone=number)
            if userphone is None:
                abort(404)
            if userphone.verification_expired:
                flash(
                    _(
                        "This number has been blocked due to too many failed verification"
                        " attempts"
                    ),
                    'danger',
                )
                # Block attempts to delete this number if verification failed.
                # It needs to be deleted in a background sweep.
                return render_redirect(url_for('account'), code=303)
            if (
                isinstance(userphone, UserPhone)
                and current_auth.user.verified_contact_count == 1
            ):
                flash(
                    _(
                        "Your account requires at least one verified email address or phone"
                        " number"
                    ),
                    'danger',
                )
                return render_redirect(url_for('account'), code=303)

        if request.method == 'POST':
            # FIXME: Confirm validation success
            user_data_changed.send(current_auth.user, changes=['phone-delete'])
        return render_delete_sqla(
            userphone,
            db,
            title=_("Confirm removal"),
            message=_("Remove phone number {phone} from your account?").format(
                phone=userphone.phone
            ),
            success=_("You have removed your number {phone}").format(
                phone=userphone.phone
            ),
            next=url_for('account'),
            delete_text=_("Remove"),
        )

    @route('phone/<number>/verify', methods=['GET', 'POST'], endpoint='verify_phone')
    def verify_phone(self, number: str) -> ReturnView:
        phoneclaim = UserPhoneClaim.query.filter_by(
            user=current_auth.user, phone=number
        ).one_or_404()
        if phoneclaim.verification_expired:
            flash(
                _("You provided an incorrect verification code too many times"),
                'danger',
            )
            # Block attempts to verify this number, but also keep the claim so that a
            # new claim cannot be made. A periodic sweep to delete old claims is needed.
            return render_redirect(url_for('account'), code=303)

        form = VerifyPhoneForm()
        form.phoneclaim = phoneclaim
        if form.validate_on_submit():
            if UserPhone.get(phoneclaim.phone) is None:
                # If there are no existing phone numbers, this will be a primary
                primary = not current_auth.user.phones
                userphone = UserPhone(
                    user=current_auth.user, phone=phoneclaim.phone, gets_text=True
                )
                userphone.primary = primary
                db.session.add(userphone)
                db.session.delete(phoneclaim)
                db.session.commit()
                flash(_("Your phone number has been verified"), 'success')
                user_data_changed.send(current_auth.user, changes=['phone'])
                return render_redirect(url_for('account'), code=303)
            db.session.delete(phoneclaim)
            db.session.commit()
            flash(
                _("This phone number has already been claimed by another user"),
                'danger',
            )
        elif form.is_submitted():
            phoneclaim.verification_attempts += 1
            db.session.commit()
        return render_form(
            form=form,
            title=_("Verify phone number"),
            formid='phone_verify',
            submit=_("Verify"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    # Userid is a path here because obsolete OpenID ids are URLs (both direct and via
    # Google's pre-OAuth2 OpenID protocol)
    @route(
        'extid/<service>/<path:userid>/remove',
        methods=['GET', 'POST'],
        endpoint='remove_extid',
    )
    @requires_sudo
    def remove_extid(self, service: str, userid: str) -> ReturnView:
        extid = UserExternalId.query.filter_by(
            user=current_auth.user, service=service, userid=userid
        ).one_or_404()
        return render_delete_sqla(
            extid,
            db,
            title=_("Confirm removal"),
            message=_(
                "Remove {service} account ‘{username}’ from your account?"
            ).format(
                service=login_registry[extid.service].title, username=extid.username
            ),
            success=_("You have removed the {service} account ‘{username}’").format(
                service=login_registry[extid.service].title, username=extid.username
            ),
            next=url_for('account'),
            delete_text=_("Remove"),
        )


AccountView.init_app(app)


# --- Compatibility routes -------------------------------------------------------------

# Retained for future hasjob integration
# @hasjobapp.route('/account/sudo', endpoint='account_sudo')
def otherapp_account_sudo() -> ReturnResponse:
    next_url = request.args.get('next')
    if next_url:
        return redirect(app_url_for(app, 'account_sudo', next=next_url))
    return redirect(app_url_for(app, 'account_sudo'))
