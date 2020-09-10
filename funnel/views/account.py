from collections import Counter, namedtuple

from flask import Markup, abort, current_app, escape, flash, redirect, request, url_for

import base58
import geoip2.errors
import user_agents

from baseframe import _
from baseframe.forms import (
    Form,
    render_delete_sqla,
    render_form,
    render_message,
    render_redirect,
)
from coaster.auth import current_auth
from coaster.utils import for_tsquery
from coaster.views import (
    ClassView,
    get_next_url,
    load_model,
    render_with,
    requestargs,
    route,
)

from .. import app, funnelapp, lastuserapp
from ..forms import (
    AccountForm,
    EmailPrimaryForm,
    LogoutForm,
    ModeratorReportForm,
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
    MODERATOR_REPORT_TYPE,
    AccountPasswordNotification,
    Comment,
    CommentModeratorReport,
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
from ..transports import TransportConnectionError, sms
from ..utils import abort_null
from .email import send_email_verify_link
from .helpers import (
    app_url_for,
    autoset_timezone_and_locale,
    progressive_rate_limit_validator,
    validate_rate_limit,
)
from .login_session import login_internal, logout_internal, requires_login
from .notification import dispatch_notification


def send_phone_verify_code(phoneclaim):
    msg = SMSMessage(
        phone_number=phoneclaim.phone,
        message=current_app.config['SMS_VERIFICATION_TEMPLATE'].format(
            code=phoneclaim.verification_code
        ),
    )
    # Now send this
    try:
        msg.transactionid = sms.send(msg.phone_number, msg.message)
        db.session.add(msg)
    except TransportConnectionError:
        flash(_("Unable to send a message right now. Please try again"))


def blake2b_b58(text):
    """
    Determine if given text is a 128 or 160-bit BLAKE2b hash (rendered in UUID58).

    Returns a dict that can be passed as kwargs to model loader. This function is
    temporary until the switch to email_hash-based lookup in a few days (in June 2020).
    """
    try:
        hash_bytes = base58.b58decode(text.encode())
        return {('blake2b' if len(hash_bytes) == 16 else 'blake2b160'): hash_bytes}
    except ValueError:
        abort(400)  # Parameter isn't valid Base58


@User.views()
def emails_sorted(obj):
    """Sorted list of email addresses, for account page UI"""
    primary = obj.primary_email
    items = sorted(obj.emails, key=lambda i: (i != primary, i.email))
    return items


@User.views()
def phones_sorted(obj):
    """Sorted list of email addresses, for account page UI"""
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
    current_section = 'account'  # needed for showing active tab
    SavedProjectForm = SavedProjectForm

    @route('', endpoint='account')
    @requires_login
    @render_with('account.html.jinja2')
    def account(self):
        logout_form = LogoutForm(user=current_auth.user)
        primary_email_form = EmailPrimaryForm()
        primary_phone_form = PhonePrimaryForm()
        service_forms = {}
        for service, provider in login_registry.items():
            if provider.at_login and provider.form is not None:
                service_forms[service] = provider.get_form()
        return {
            'user': current_auth.user.current_access(),
            'logout_form': logout_form,
            'primary_email_form': primary_email_form,
            'primary_phone_form': primary_phone_form,
            'service_forms': service_forms,
            'login_registry': login_registry,
        }

    @route('saved', endpoint='saved')
    @requires_login
    @render_with('account_saved.html.jinja2')
    def saved(self):
        return {'saved_projects': current_auth.user.saved_projects}

    @route('siteadmin/comments', endpoint='siteadmin_comments', methods=['GET', 'POST'])
    @requires_login
    @render_with('siteadmin_comments.html.jinja2')
    @requestargs(('query', abort_null), ('page', int), ('per_page', int))
    def siteadmin_comments(self, query='', page=None, per_page=100):
        if not (
            current_auth.user.is_comment_moderator
            or current_auth.user.is_user_moderator
        ):
            return abort(403)

        comments = Comment.query.filter(~(Comment.state.REMOVED)).order_by(
            Comment.created_at.desc()
        )
        if query:
            comments = comments.join(User).filter(
                db.or_(
                    Comment.search_vector.match(for_tsquery(query or '')),
                    User.search_vector.match(for_tsquery(query or '')),
                )
            )

        pagination = comments.paginate(page=page, per_page=per_page)

        return {
            'query': query,
            'comments': pagination.items,
            'total_comments': pagination.total,
            'pages': list(range(1, pagination.pages + 1)),  # list of page numbers
            'current_page': pagination.page,
            'comment_spam_form': Form(),
        }

    @route(
        'siteadmin/comments/markspam',
        endpoint='siteadmin_comments_spam',
        methods=['POST'],
    )
    @requires_login
    def siteadmin_comments_spam(self):
        if not (
            current_auth.user.is_comment_moderator
            or current_auth.user.is_user_moderator
        ):
            return abort(403)

        comment_spam_form = Form()
        comment_spam_form.form_nonce.data = comment_spam_form.form_nonce.default()
        if comment_spam_form.validate_on_submit():
            comments = Comment.query.filter(
                Comment.uuid_b58.in_(request.form.getlist('comment_id'))
            )
            for comment in comments:
                CommentModeratorReport.submit(actor=current_auth.user, comment=comment)
            db.session.commit()
            flash(_("Comment(s) successfully reported as spam"), category='info')
        else:
            flash(
                _("There was a problem marking the comments as spam. Please try again"),
                category='error',
            )

        return redirect(url_for('siteadmin_comments'))

    @route('siteadmin/review/comments', endpoint='siteadmin_review_comments_random')
    @requires_login
    def siteadmin_review_comments_random(self, report=None):
        if not current_auth.user.is_comment_moderator:
            return abort(403)

        random_report = CommentModeratorReport.get_one(exclude_user=current_auth.user)
        if random_report is not None:
            return redirect(
                url_for('siteadmin_review_comment', report=random_report.uuid_b58)
            )
        else:
            flash(_("There is no comment report no review at this moment"), 'error')
            return redirect(url_for('account'))

    @route(
        'siteadmin/review/comments/<report>',
        endpoint='siteadmin_review_comment',
        methods=['GET', 'POST'],
    )
    @render_with('siteadmin_review_comment.html.jinja2')
    @requires_login
    def siteadmin_review_comment(self, report):
        if not current_auth.user.is_comment_moderator:
            return abort(403)

        report = CommentModeratorReport.query.filter_by(uuid_b58=report).one_or_404()

        if report.user == current_auth.user:
            flash(_("You cannot review your own report"), 'error')
            return redirect(url_for('siteadmin_review_comments_random'))

        # get all existing reports for the same comment
        existing_reports = CommentModeratorReport.get_all(
            exclude_user=current_auth.user
        ).filter_by(comment_id=report.comment_id)

        if report not in existing_reports:
            # current report should be in the existing unreviewed reports
            flash(_("You cannot review same comment twice"), 'error')
            return redirect(url_for('siteadmin_review_comments_random'))

        report_form = ModeratorReportForm()
        report_form.form_nonce.data = report_form.form_nonce.default()

        if report_form.validate_on_submit():
            # get other reports for same comment
            # existing report count will be greater than 0 because
            # current report exists and it's not by the current user.
            report_counter = Counter(
                [report.report_type for report in existing_reports]
                + [report_form.report_type.data]
            )
            # if there is already a report for this comment
            ReportCounter = namedtuple('ReportCounter', ['report_type', 'frequency'])

            most_common_two = [
                ReportCounter(report_type, frequency)
                for report_type, frequency in report_counter.most_common(2)
            ]
            # Possible values of most_common_two -
            # - [(1, 2)] - if both existing and current reports are same or
            # - [(1, 2), (0, 1), (report_type, frequency)] - conflicting reports
            if (
                len(most_common_two) == 1
                or most_common_two[0].frequency > most_common_two[1].frequency
            ):
                if most_common_two[0].report_type == MODERATOR_REPORT_TYPE.SPAM:
                    report.comment.mark_spam()
                elif most_common_two[0].report_type == MODERATOR_REPORT_TYPE.OK:
                    if report.comment.state.SPAM:
                        report.comment.mark_not_spam()
                CommentModeratorReport.query.filter_by(comment=report.comment).delete()
            else:
                # current report is different from existing report and
                # no report has majority frequency.
                # e.g. existing report was spam, current report is not spam,
                # we'll create the new report and wait for a 3rd report.
                new_report = CommentModeratorReport(
                    user=current_auth.user,
                    comment=report.comment,
                    report_type=report_form.report_type.data,
                )
                db.session.add(new_report)
            db.session.commit()

            # Redirect to a new report
            return redirect(url_for('siteadmin_review_comments_random'))
        else:
            app.logger.debug(report_form.errors)

        return {
            'report': report,
            'report_form': report_form,
        }


@route('/account')
class OtherAppAccountView(ClassView):
    @route('', endpoint='account')
    @requires_login
    def account(self):
        return redirect(app_url_for(app, 'account', _external=True))


AccountView.init_app(app)
OtherAppAccountView.init_app(funnelapp)
OtherAppAccountView.init_app(lastuserapp)


@app.route(
    '/account/edit',
    methods=['GET', 'POST'],
    defaults={'newprofile': False},
    endpoint='account_edit',
)
@app.route(
    '/account/new',
    methods=['GET', 'POST'],
    defaults={'newprofile': True},
    endpoint='account_new',
)
@requires_login
def account_edit(newprofile=False):
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
        else:
            return render_redirect(url_for('account'), code=303)
    if newprofile:
        return render_form(
            form,
            title=_("Update account"),
            formid='account_new',
            submit=_("Continue"),
            message=Markup(
                _(
                    "Hello, <strong>{fullname}</strong>. Please spare a minute to fill"
                    " out your account"
                ).format(fullname=escape(current_auth.user.fullname))
            ),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )
    else:
        return render_form(
            form,
            title=_("Edit account"),
            formid='account_edit',
            submit=_("Save changes"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )


# FIXME: Don't modify db on GET. Autosubmit via JS and process on POST
@app.route('/account/confirm/<email_hash>/<secret>')
@lastuserapp.route('/confirm/<email_hash>/<secret>')
@requires_login
def confirm_email(email_hash, secret):
    kwargs = blake2b_b58(email_hash)
    emailclaim = UserEmailClaim.get_by(verification_code=secret, **kwargs)
    if emailclaim is not None:
        emailclaim.email_address.mark_active()
        if 'verify' in emailclaim.permissions(current_auth.user):
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
                else:
                    return render_message(
                        title=_("Email address already verified"),
                        message=Markup(
                            _(
                                "Hello <strong>{fullname}</strong>! Your email address"
                                " <code>{email}</code> has already been verified"
                            ).format(
                                fullname=escape(claimed_user.fullname),
                                email=escape(claimed_email),
                            )
                        ),
                    )

            useremail = emailclaim.user.add_email(
                emailclaim.email,
                primary=emailclaim.user.email is None,
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
                        "Hello <strong>{fullname}</strong>! "
                        "Your email address <code>{email}</code> has now been verified"
                    ).format(
                        fullname=escape(useremail.user.fullname),
                        email=escape(useremail.email),
                    )
                ),
            )
        else:
            return render_message(
                title=_("This was not for you"),
                message=_(
                    "You’ve opened an email verification link that was meant for"
                    " another user. If you are managing multiple accounts, please login"
                    " with the correct account and open the link again."
                ),
                code=403,
            )
    else:
        return render_message(
            title=_("Expired confirmation link"),
            message=_(
                "The confirmation link you clicked on is either invalid or has expired."
            ),
            code=404,
        )


@app.route('/account/password', methods=['GET', 'POST'])
@requires_login
def change_password():
    if not current_auth.user.pw_hash:
        form = PasswordCreateForm(edit_user=current_auth.user)
    else:
        form = PasswordChangeForm(edit_user=current_auth.user)
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
    return render_form(
        form=form,
        title=_("Change password"),
        formid='password-change',
        submit=_("Change password"),
        ajax=False,
        template='account_formlayout.html.jinja2',
    )


@app.route('/account/email/new', methods=['GET', 'POST'])
@requires_login
def add_email():
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


@app.route('/account/email/makeprimary', methods=['POST'])
@requires_login
def make_email_primary():
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
            flash(_("No such email address is linked to this user account"), 'danger')
    else:
        flash(_("Please select an email address"), 'danger')
    return render_redirect(url_for('account'), code=303)


@app.route('/account/phone/makeprimary', methods=['POST'])
@requires_login
def make_phone_primary():
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
            flash(_("No such phone number is linked to this user account"), 'danger')
    else:
        flash(_("Please select a phone number"), 'danger')
    return render_redirect(url_for('account'), code=303)


@app.route('/account/email/<email_hash>/remove', methods=['GET', 'POST'])
@requires_login
def remove_email(email_hash):
    useremail = UserEmail.get_for(user=current_auth.user, email_hash=email_hash)
    if not useremail:
        useremail = UserEmailClaim.get_for(
            user=current_auth.user, email_hash=email_hash
        )
        if not useremail:
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


@app.route('/account/email/<email_hash>/verify', methods=['GET', 'POST'])
@requires_login
def verify_email(email_hash):
    """
    If the user has a pending email verification but has lost the email, allow them to
    send themselves another verification email. This endpoint is only linked to from
    the account page under the list of email addresses pending verification.
    """
    useremail = UserEmail.get(email_hash=email_hash)
    if useremail and useremail.user == current_auth.user:
        # If an email address is already verified (this should not happen unless the
        # user followed a stale link), tell them it's done -- but only if the email
        # address belongs to this user, to prevent this endpoint from being used as a
        # probe for email addresses in the database.
        flash(_("This email address is already verified"), 'danger')
        return render_redirect(url_for('account'), code=303)

    # Get the existing email claim that we're resending a verification link for
    emailclaim = UserEmailClaim.get_for(user=current_auth.user, email_hash=email_hash)
    if not emailclaim:
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
            "We will resend the verification email to {email}.".format(
                email=emailclaim.email
            )
        ),
        formid="email_verify",
        submit=_("Send"),
        template='account_formlayout.html.jinja2',
    )


@app.route('/account/phone/new', methods=['GET', 'POST'])
@requires_login
def add_phone():
    form = NewPhoneForm()
    if form.validate_on_submit():
        userphone = UserPhoneClaim.get_for(
            user=current_auth.user, phone=form.phone.data
        )
        if userphone is None:
            userphone = UserPhoneClaim(user=current_auth.user, phone=form.phone.data)
            db.session.add(userphone)
        try:
            current_auth.user.main_notification_preferences.by_sms = (
                form.enable_notifications.data
            )
            send_phone_verify_code(userphone)
            # Commit after sending because send_phone_verify_code saves the message sent
            db.session.commit()
            flash(
                _("A verification code has been sent to your phone number"), 'success'
            )
            user_data_changed.send(current_auth.user, changes=['phone-claim'])
            return render_redirect(
                url_for('verify_phone', number=userphone.phone), code=303
            )
        except ValueError as e:
            db.session.rollback()
            form.phone.errors.append(str(e))
    return render_form(
        form=form,
        title=_("Add a phone number"),
        formid='phone_add',
        submit=_("Verify phone"),
        ajax=False,
        template='account_formlayout.html.jinja2',
    )


@app.route('/account/phone/<number>/remove', methods=['GET', 'POST'])
@requires_login
def remove_phone(number):
    userphone = UserPhone.get(phone=number)
    if userphone is None or userphone.user != current_auth.user:
        userphone = UserPhoneClaim.get_for(user=current_auth.user, phone=number)
        if not userphone:
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
        success=_("You have removed your number {phone}").format(phone=userphone.phone),
        next=url_for('account'),
        delete_text=_("Remove"),
    )


@app.route('/account/phone/<number>/verify', methods=['GET', 'POST'])
@requires_login
@load_model(UserPhoneClaim, {'phone': 'number'}, 'phoneclaim', permission='verify')
def verify_phone(phoneclaim):
    if phoneclaim.verification_expired:
        flash(_("You provided an incorrect verification code too many times"), 'danger')
        # Block attempts to verify this number, but also keep the claim so that a new
        # claim cannot be made. A periodic sweep to delete old claims is needed.
        return render_redirect(url_for('account'), code=303)

    form = VerifyPhoneForm()
    form.phoneclaim = phoneclaim
    if form.validate_on_submit():
        if UserPhone.get(phoneclaim.phone) is None:
            if not current_auth.user.phones:
                primary = True
            else:
                primary = False
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
        else:
            db.session.delete(phoneclaim)
            db.session.commit()
            flash(
                _("This phone number has already been claimed by another user"),
                'danger',
            )
    elif request.method == 'POST':
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


# Userid is a path here because obsolete OpenID ids are URLs (both direct and via Google)
@app.route('/account/extid/<service>/<path:userid>/remove', methods=['GET', 'POST'])
@requires_login
@load_model(
    UserExternalId,
    {'service': 'service', 'userid': 'userid'},
    'extid',
    permission='delete_extid',
)
def remove_extid(extid):
    num_extids = len(current_auth.user.externalids)
    has_pw_hash = bool(current_auth.user.pw_hash)
    if not has_pw_hash and num_extids == 1:
        flash(
            _(
                "You do not have a password set. So you must have at least one external"
                " ID enabled."
            ),
            'danger',
        )
        return render_redirect(url_for('account'), code=303)
    return render_delete_sqla(
        extid,
        db,
        title=_("Confirm removal"),
        message=_("Remove {service} account ‘{username}’ from your account?").format(
            service=login_registry[extid.service].title, username=extid.username
        ),
        success=_("You have removed the {service} account ‘{username}’").format(
            service=login_registry[extid.service].title, username=extid.username
        ),
        next=url_for('account'),
        delete_text=_("Remove"),
    )


# --- Lastuserapp legacy routes --------------------------------------------------------

# Redirect from old URL in previously sent out verification emails
@lastuserapp.route('/profile/email/<email_hash>/verify')
def verify_email_old(email_hash):
    return redirect(app_url_for(app, 'verify_email', email_hash=email_hash), code=301)


# Redirect from Lastuser's account edit page
@lastuserapp.route(
    '/account/edit',
    methods=['GET', 'POST'],
    defaults={'newprofile': False},
    endpoint='account_edit',
)
@lastuserapp.route(
    '/account/new',
    methods=['GET', 'POST'],
    defaults={'newprofile': True},
    endpoint='account_new',
)
def lastuser_account_edit(newprofile):
    return redirect(app_url_for(app, 'account_new' if newprofile else 'account_edit'))
