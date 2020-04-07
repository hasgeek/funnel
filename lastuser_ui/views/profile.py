# -*- coding: utf-8 -*-

from flask import abort, flash, redirect, render_template, request, url_for

from baseframe import _
from baseframe.forms import render_delete_sqla, render_form, render_redirect
from coaster.auth import current_auth
from coaster.views import load_model
from lastuser_core import login_registry
from lastuser_core.models import (
    UserEmail,
    UserEmailClaim,
    UserExternalId,
    UserPhone,
    UserPhoneClaim,
    db,
)
from lastuser_core.signals import user_data_changed
from lastuser_oauth.forms import PasswordChangeForm, PasswordResetForm
from lastuser_oauth.mailclient import send_email_verify_link
from lastuser_oauth.views.helpers import requires_login

from .. import lastuser_ui
from ..forms import (
    EmailPrimaryForm,
    NewEmailAddressForm,
    NewPhoneForm,
    PhonePrimaryForm,
    VerifyEmailForm,
    VerifyPhoneForm,
)
from .sms import send_phone_verify_code


@lastuser_ui.route('/profile', defaults={'path': None})
@lastuser_ui.route('/profile/<path:path>')
@requires_login
def profile(path=None):
    if path is not None:
        return redirect('/account/%s' % path)
    else:
        return redirect('/account')


@lastuser_ui.route('/account')
@requires_login
def account():
    primary_email_form = EmailPrimaryForm()
    primary_phone_form = PhonePrimaryForm()
    service_forms = {}
    for service, provider in login_registry.items():
        if provider.at_login and provider.form is not None:
            service_forms[service] = provider.get_form()
    return render_template(
        'account.html.jinja2',
        primary_email_form=primary_email_form,
        primary_phone_form=primary_phone_form,
        service_forms=service_forms,
        login_registry=login_registry,
    )


@lastuser_ui.route('/account/password', methods=['GET', 'POST'])
@requires_login
def change_password():
    if not current_auth.user.pw_hash:
        form = PasswordResetForm()
        form.edit_user = current_auth.user
        del form.username
    else:
        form = PasswordChangeForm()
        form.edit_user = current_auth.user
    if form.validate_on_submit():
        current_auth.user.password = form.password.data
        db.session.commit()
        flash(_("Your new password has been saved"), category='success')
        return render_redirect(url_for('.account'), code=303)
    return render_form(
        form=form,
        title=_("Change password"),
        formid='changepassword',
        submit=_("Change password"),
        ajax=True,
    )


@lastuser_ui.route('/account/email/new', methods=['GET', 'POST'])
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
            db.session.commit()
        send_email_verify_link(useremail)
        flash(_("We sent you an email to confirm your address"), 'success')
        user_data_changed.send(current_auth.user, changes=['email-claim'])
        return render_redirect(url_for('.account'), code=303)
    return render_form(
        form=form,
        title=_("Add an email address"),
        formid='email_add',
        submit=_("Add email"),
        ajax=True,
    )


@lastuser_ui.route('/account/email/makeprimary', methods=['POST'])
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
    return render_redirect(url_for('.account'), code=303)


@lastuser_ui.route('/account/phone/makeprimary', methods=['POST'])
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
    return render_redirect(url_for('.account'), code=303)


@lastuser_ui.route('/account/email/<md5sum>/remove', methods=['GET', 'POST'])
@requires_login
def remove_email(md5sum):
    useremail = UserEmail.get_for(user=current_auth.user, md5sum=md5sum)
    if not useremail:
        useremail = UserEmailClaim.get_for(user=current_auth.user, md5sum=md5sum)
        if not useremail:
            abort(404)
    if isinstance(useremail, UserEmail) and useremail.primary:
        flash(_("You cannot remove your primary email address"), 'danger')
        return render_redirect(url_for('.account'), code=303)
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
        next=url_for('.account'),
        delete_text=_("Remove"),
    )


# Redirect from old URL in previously sent out verification emails
@lastuser_ui.route('/profile/email/<md5sum>/verify')
def verify_email_old(md5sum):
    return redirect(url_for('verify_email', md5sum=md5sum), code=301)


@lastuser_ui.route('/account/email/<md5sum>/verify', methods=['GET', 'POST'])
@requires_login
def verify_email(md5sum):
    """
    If the user has a pending email verification but has lost the email, allow them to
    send themselves another verification email. This endpoint is only linked to from
    the account page under the list of email addresses pending verification.
    """
    useremail = UserEmail.get(md5sum=md5sum)
    if useremail and useremail.user == current_auth.user:
        # If an email address is already verified (this should not happen unless the
        # user followed a stale link), tell them it's done -- but only if the email
        # address belongs to this user, to prevent this endpoint from being used as a
        # probe for email addresses in the database.
        flash(_("This email address is already verified"), 'danger')
        return render_redirect(url_for('.account'), code=303)

    # Get the existing email claim that we're resending a verification link for
    emailclaim = UserEmailClaim.get_for(user=current_auth.user, md5sum=md5sum)
    if not emailclaim:
        abort(404)
    verify_form = VerifyEmailForm()
    if verify_form.validate_on_submit():
        send_email_verify_link(emailclaim)
        flash(_("The verification email has been sent to this address"), 'success')
        return render_redirect(url_for('.account'), code=303)
    return render_form(
        form=verify_form,
        title=_("Resend the verification email?"),
        message=_(
            "We will resend the verification email to '{email}'".format(
                email=emailclaim.email
            )
        ),
        formid="email_verify",
        submit=_("Send"),
        cancel_url=url_for('.account'),
    )


@lastuser_ui.route('/account/phone/new', methods=['GET', 'POST'])
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
            send_phone_verify_code(userphone)
            db.session.commit()  # Commit after sending because send_phone_verify_code saves the message sent
            flash(_("We sent a verification code to your phone number"), 'success')
            user_data_changed.send(current_auth.user, changes=['phone-claim'])
            return render_redirect(
                url_for('.verify_phone', number=userphone.phone), code=303
            )
        except ValueError as e:
            db.session.rollback()
            form.phone.errors.append(str(e))
    return render_form(
        form=form,
        title=_("Add a phone number"),
        formid='phone_add',
        submit=_("Verify phone"),
        ajax=True,
    )


@lastuser_ui.route('/account/phone/<number>/remove', methods=['GET', 'POST'])
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
                    "This number has been blocked due to too many failed verification attempts"
                ),
                'danger',
            )
            # Block attempts to delete this number if verification failed.
            # It needs to be deleted in a background sweep.
            return render_redirect(url_for('.account'), code=303)

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
        next=url_for('.account'),
        delete_text=_("Remove"),
    )


@lastuser_ui.route('/account/phone/<number>/verify', methods=['GET', 'POST'])
@requires_login
@load_model(UserPhoneClaim, {'phone': 'number'}, 'phoneclaim', permission='verify')
def verify_phone(phoneclaim):
    if phoneclaim.verification_expired:
        flash(_("You provided an incorrect verification code too many times"), 'danger')
        # Block attempts to verify this number, but also keep the claim so that a new
        # claim cannot be made. A periodic sweep to delete old claims is needed.
        return render_redirect(url_for('.account'), code=303)

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
            return render_redirect(url_for('.account'), code=303)
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
        ajax=True,
    )


# Userid is a path here because obsolete OpenID ids are URLs (both direct and via Google)
@lastuser_ui.route(
    '/account/extid/<service>/<path:userid>/remove', methods=['GET', 'POST']
)
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
                "You do not have a password set. So you must have at least one external ID enabled."
            ),
            'danger',
        )
        return render_redirect(url_for('.account'), code=303)
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
        next=url_for('.account'),
        delete_text=_("Remove"),
    )
