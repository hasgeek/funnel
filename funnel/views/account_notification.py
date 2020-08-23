from datetime import datetime

from flask import flash, redirect, request, session, url_for
import itsdangerous.exc

from baseframe import _
from baseframe.forms import render_form, render_message
from coaster.auth import current_auth
from coaster.utils import getbool
from coaster.views import ClassView, render_with, requestargs, route

from .. import app
from ..forms import SetNotificationPreferenceForm, UnsubscribeForm, transport_labels
from ..models import (
    NOTIFICATION_CATEGORY,
    EmailAddress,
    NotificationPreferences,
    User,
    db,
    notification_type_registry,
)
from ..serializers import token_serializer
from ..transports import platform_transports
from .helpers import metarefresh_redirect
from .login_session import requires_login

# --- Account notifications tab --------------------------------------------------------


@route('/account/notifications')
class AccountNotificationView(ClassView):
    # TODO: This class does not use ModelView on User because some routes do not require
    # a logged in user. While it would be nice to have current_auth.user.url_for('...'),
    # this does not work when there is no current_auth.user. However, this can be
    # handled using an explicit endpoint name and url_for(endpoint_name), so maybe we
    # should use a ModelView after all.

    current_section = 'notification_preferences'

    @route('', endpoint='notification_preferences')
    @requires_login
    @render_with('notification_preferences.html.jinja2')
    def notification_preferences(self):
        main_preferences = current_auth.user.main_notification_preferences
        user_preferences = current_auth.user.notification_preferences
        preferences = {
            key: {'title': value, 'types': []}
            for key, value in NOTIFICATION_CATEGORY.items()
        }
        for ntype, ncls in notification_type_registry.items():
            preferences[ncls.category]['types'].append(
                {
                    'notification_type': ntype,
                    'description': ncls.description,
                    'preferences': {
                        transport: user_preferences[ntype].by_transport(transport)
                        for transport in platform_transports
                    }
                    if ntype in user_preferences
                    else None,
                }
            )
        # Remove empty categories
        for key in list(preferences):
            if not preferences[key]['types']:
                del preferences[key]

        return {
            'main_preferences': {
                transport: main_preferences.by_transport(transport)
                for transport in platform_transports
            },
            'preferences': preferences,
            # Transports is an ordered list (priority, not alphabetic)
            'transports': [
                transport
                for transport, enabled in platform_transports.items()
                if enabled
            ],
            # Details as a separate dictionary as they don't preserve order by priority
            # when passed through JSON
            'transport_details': {
                transport: {
                    'available': current_auth.user.has_transport(transport),
                    'title': transport_labels[transport].title,
                    'requirement': transport_labels[transport].requirement,
                    'switch': transport_labels[transport].switch,
                }
                for transport, enabled in platform_transports.items()
                if enabled
            },
        }

    @route('set', endpoint='set_notification_preference', methods=['POST'])
    @requires_login
    @render_with(json=True)
    def set_notification_preference(self):
        """Set one notification preference."""
        form = SetNotificationPreferenceForm()
        del form.form_nonce
        if form.validate():
            if (
                form.notification_type.data
                not in current_auth.user.notification_preferences
            ):
                prefs = NotificationPreferences(
                    user=current_auth.user,
                    notification_type=form.notification_type.data,
                )
                db.session.add(prefs)
                is_new = True
            else:
                prefs = current_auth.user.notification_preferences[
                    form.notification_type.data
                ]
                is_new = False
            prefs.set_transport(form.transport.data, form.enabled.data)
            db.session.commit()
            return (
                {
                    'status': 'ok',
                    'notification_type': prefs.notification_type,
                    'preferences': {
                        transport: prefs.by_transport(transport)
                        for transport in platform_transports
                    },
                    'message': form.status_message(),
                },
                201 if is_new else 200,
            )
        return (
            {
                'status': 'error',
                'error': 'csrf',
                'error_description': form.status_message(),
            },
            400,
        )

    @route('unsubscribe/<token>', endpoint='notification_unsubscribe')
    @route(
        'unsubscribe',
        defaults={'token': None},
        endpoint='notification_unsubscribe',
        methods=['GET', 'POST'],
    )
    @requestargs(('cookietest', getbool))
    def unsubscribe(self, token, cookietest=False):
        # This route strips the token from the URL before rendering the page, to avoid
        # leaking the token to web analytics software.

        # Step 1: Sanity check: someone loaded this URL without a token at all.
        # Send them away
        if not token and (
            (request.method == 'GET' and 'temp_token' not in session)
            or (request.method == 'POST' and 'token' not in request.form)
        ):
            return redirect(url_for('notification_preferences'))

        # Step 2: We have a URL token, but no `cookietest=1` in the URL. Copy token into
        # session and reload the page with the flag set
        if token and not cookietest:
            session['temp_token'] = token
            # Use naive datetime as the session can't handle tz-aware datetimes
            session['temp_token_at'] = datetime.utcnow()
            # These values are removed from the session in 10 minutes by
            # :func:`funnel.views.login_session.clear_expired_temp_token` if the user
            # abandons this page.

            # Reconstruct current URL with ?cookietest=1 or &cookietest=1 appended
            # and reload the page
            if request.query_string:
                return redirect(request.url + '&cookietest=1')
            return redirect(request.url + '?cookietest=1')

        # Step 3a: We have a URL token and cookietest is now set, but token is missing
        # from session. That typically means the browser is refusing to set cookies
        # on 30x redirects that originated off-site (such as a webmail app). Do a
        # meta-refresh redirect instead. It is less secure because browser extensions
        # may be able to read the URL during the brief period the page is rendered,
        # but so far there has been no indication of cookies not being set.
        if token and 'temp_token' not in session:
            session['temp_token'] = token
            session['temp_token_at'] = datetime.utcnow()
            return metarefresh_redirect(
                url_for('notification_unsubscribe')
                + ('?' + request.query_string.decode())
                if request.query_string
                else ''
            )

        # Step 3b: We have a URL token and cookietest is now set, and token is also in
        # session. Great! No browser cookie problem, so redirect again to remove the
        # token from the URL. This will hide it from web analytics software such as
        # Google Analytics and Matomo.
        if token and 'temp_token' in session:
            # Browser is okay with cookies. Do a 302 redirect
            # Strip out `cookietest=1` from the redirected URL
            return redirect(
                (
                    url_for('notification_unsubscribe')
                    + ('?' + request.query_string.decode())
                    if request.query_string
                    else ''
                )
                .replace('?cookietest=1&', '?')  # If cookietest is somehow at start
                .replace('?cookietest=1', '')  # If it's solo
                .replace('&cookietest=1', '')  # If it's in the middle or end
            )

        # Step 4. We have a token and it's been stripped from the URL. Process it.
        try:
            # Token will be in session in the GET request, and will be in request.form
            # in the POST request. We'll move it over during the GET request
            payload = token_serializer().loads(
                session.get('temp_token') or request.form['token'],
                max_age=365 * 24 * 60 * 60,
            )
        except itsdangerous.exc.SignatureExpired:
            # Link has expired. It's been over a year!
            session.pop('temp_token', None)
            session.pop('temp_token_at', None)
            flash(
                _(
                    "This unsubscribe link has expired."
                    " However, you can manage your settings from your account page"
                ),
                'error',
            )
            return redirect(url_for('notification_preferences'), code=303)
        except itsdangerous.exc.BadData:
            session.pop('temp_token', None)
            session.pop('temp_token_at', None)
            flash(
                _(
                    "This unsubscribe link is invalid."
                    " However, you can manage your settings from your account page"
                ),
                'error',
            )
            return redirect(url_for('notification_preferences'), code=303)

        # Step 5. Validate whether the token matches the current user, if any
        # Do not allow links to be used across accounts.
        if current_auth.user and current_auth.user.buid != payload['buid']:
            return render_message(
                title=_("Unauthorized unsubscribe link"),
                message=_(
                    "This unsubscribe link is for someone else’s account. Please logout"
                    " or use an incognito/private browsing session to use this link."
                ),
            )

        # Step 6. Load the user. The contents of `payload` are defined in
        # :meth:`NotificationView.unsubscribe_token` above
        user = User.get(buid=payload['buid'])
        if payload['transport'] == 'email' and 'hash' in payload:
            email_address = EmailAddress.get(email_hash=payload['hash'])
            email_address.mark_active()
            db.session.commit()

        # Step 7. Ask the user to confirm unsubscribe. Do not unsubscribe on a GET
        # request as it may be triggered by link previews (for transports other than
        # email, or when an email is copy-pasted into a messenger app).
        form = UnsubscribeForm(
            edit_user=user,
            transport=payload['transport'],
            notification_type=payload['notification_type'],
        )
        # Move the token from session to form. The session is swept every 10 minutes,
        # so if the user opens an unsubscribe link, wanders away and comes back later,
        # it'll be gone from session. It's safe for longer in the form, and doesn't
        # bear the leakage risk of being in the URL where analytics software can log it.
        if 'temp_token' in session:
            form.token.data = session.pop('temp_token')
            session.pop('temp_token_at', None)
        if form.validate_on_submit():
            form.save_to_user()
            db.session.commit()
            return render_message(
                title=_("Preferences saved"),
                message=_("Your notification preferences have been updated"),
            )
        return render_form(
            form=form,
            title=_("Unsubscribe from notifications"),
            formid='unsubscribe-preferences',
            submit=_("Save preferences"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )


AccountNotificationView.init_app(app)
