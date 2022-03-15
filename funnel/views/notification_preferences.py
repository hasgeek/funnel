from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from flask import abort, flash, redirect, request, session, url_for
import itsdangerous

from baseframe import _, __
from baseframe.forms import render_form, render_message
from coaster.auth import current_auth
from coaster.utils import getbool
from coaster.views import ClassView, render_with, requestargs, route

from .. import app
from ..forms import SetNotificationPreferenceForm, UnsubscribeForm, transport_labels
from ..models import (
    EmailAddress,
    NotificationPreferences,
    User,
    db,
    notification_categories,
    notification_type_registry,
)
from ..serializers import token_serializer
from ..transports import platform_transports
from ..typing import ReturnRenderWith
from .helpers import (
    metarefresh_redirect,
    retrieve_cached_token,
    session_timeouts,
    validate_rate_limit,
)
from .login_session import requires_login

session_timeouts['unsub_token'] = timedelta(minutes=15)
session_timeouts['unsub_token_type'] = timedelta(minutes=15)

# --- Account notifications tab --------------------------------------------------------

unsubscribe_link_expired = __(
    "That unsubscribe link has expired. However, you can manage your preferences from"
    " your account page"
)

unsubscribe_link_invalid = __(
    "That unsubscribe link is invalid. However, you can manage your preferences from"
    " your account page"
)


@route('/account/notifications')
class AccountNotificationView(ClassView):
    # TODO: This class does not use ModelView on User because some routes do not require
    # a logged in user. While it would be nice to have current_auth.user.url_for('...'),
    # this does not work when there is no current_auth.user. However, this can be
    # handled using an explicit endpoint name and url_for(endpoint_name), so maybe we
    # should use a ModelView after all.

    current_section = 'account'

    @route('', endpoint='notification_preferences')
    @requires_login
    @render_with('notification_preferences.html.jinja2')
    def notification_preferences(self) -> ReturnRenderWith:
        main_preferences = current_auth.user.main_notification_preferences
        user_preferences = current_auth.user.notification_preferences
        preferences = {
            ncat.priority_id: {'title': ncat.title, 'types': []}
            for ncat in notification_categories.__dict__.values()
            if ncat.available_for(current_auth.user)
        }
        commit_new_preferences = False
        for ntype, ncls in notification_type_registry.items():
            if ncls.category.priority_id in preferences:
                if ntype not in user_preferences:
                    user_preferences[ntype] = NotificationPreferences(
                        user=current_auth.user, notification_type=ntype
                    )
                    commit_new_preferences = True
                preferences[ncls.category.priority_id]['types'].append(
                    {
                        'notification_type': ntype,
                        'title': ncls.title,
                        'description': ncls.description,
                        'preferences': {
                            transport: user_preferences[ntype].by_transport(transport)
                            for transport in platform_transports
                        },
                    }
                )
        if commit_new_preferences:
            db.session.commit()
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
                    'action': transport_labels[transport].requirement_action(),
                    'switch': transport_labels[transport].switch,
                }
                for transport, enabled in platform_transports.items()
                if enabled
            },
        }

    @route('set', endpoint='set_notification_preference', methods=['POST'])
    @requires_login
    @render_with(json=True)
    def set_notification_preference(self) -> ReturnRenderWith:
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

    @route(
        'unsubscribe/<token>',
        methods=['POST'],
        endpoint='notification_unsubscribe_auto',
    )
    def unsubscribe_auto(self, token: str):
        """Implement RFC 8058 one-click auto unsubscribe for email transport."""
        # TODO: Merge this into the other handler. Unsubscribe first, then ask the user
        # if they'd like to resubscribe
        try:
            payload = token_serializer().loads(
                token, max_age=365 * 24 * 60 * 60  # Validity 1 year (365 days)
            )
        except itsdangerous.SignatureExpired:
            # Link has expired. It's been over a year!
            flash(unsubscribe_link_expired, 'error')
            return redirect(url_for('notification_preferences'), code=303)
        except itsdangerous.BadData:
            flash(unsubscribe_link_invalid, 'error')
            return redirect(url_for('notification_preferences'), code=303)

        user = User.get(buid=payload['buid'])
        if user is None:
            app.logger.error(
                "Auto unsubscribe view cannot find user with buid %s", payload['buid']
            )
            # We can't use `render_message` here because the unsubscribe token is still
            # in the URL
            flash(_("This unsubscribe link is for a non-existent user"), 'error')
            return redirect(url_for('index'), code=303)
        # Check transport again in case this endpoint is extended to other transports
        if payload['transport'] == 'email' and 'hash' in payload:
            email_address = EmailAddress.get(email_hash=payload['hash'])
            if email_address is None:
                app.logger.error(
                    "Auto unsubscribe view cannot find email address with hash %s",
                    payload['hash'],
                )
            else:
                email_address.mark_active()
        user.notification_preferences[payload['notification_type']].set_transport(
            payload['transport'], False
        )
        db.session.commit()
        # We can't use `render_message` here because the unsubscribe token is still in
        # the URL
        flash(_("You have been unsubscribed from this notification type"), 'success')
        return redirect(url_for('index'), code=303)

    @route(
        'unsubscribe/<token>',
        defaults={'token_type': 'signed'},
        methods=['GET'],
        endpoint='notification_unsubscribe',
    )
    @route(
        'bye/<token>',
        defaults={'token_type': 'cached'},
        methods=['GET', 'POST'],
        endpoint='notification_unsubscribe_short',
    )
    @route(
        'unsubscribe',
        defaults={'token': None, 'token_type': None},
        methods=['GET', 'POST'],
        endpoint='notification_unsubscribe_do',
    )
    @requestargs(('cookietest', getbool))
    def unsubscribe(
        self, token: str, token_type: Optional[str], cookietest: bool = False
    ):
        # This route strips the token from the URL before rendering the page, to avoid
        # leaking the token to web analytics software.

        # Step 1: Sanity check: someone loaded this URL without a token at all.
        # Send them away
        if not token and (
            (request.method == 'GET' and 'unsub_token' not in session)
            or (request.method == 'POST' and 'token' not in request.form)
        ):
            return redirect(url_for('notification_preferences'))

        # Step 2: We have a URL token, but no `cookietest=1` in the URL. Copy token into
        # session and reload the page with the flag set
        if token and not cookietest:
            session['unsub_token'] = token
            session['unsub_token_type'] = token_type
            # These values are removed from the session in 15 minutes by
            # :func:`funnel.views.helpers.track_temporary_session_vars` if the user
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
        if token and 'unsub_token' not in session:
            session['unsub_token'] = token
            session['unsub_token_type'] = token_type
            return metarefresh_redirect(
                url_for('notification_unsubscribe_do')
                + ('?' + request.query_string.decode())
                if request.query_string
                else ''
            )

        # Step 3b: We have a URL token and cookietest is now set, and token is also in
        # session. Great! No browser cookie problem, so redirect again to remove the
        # token from the URL. This will hide it from web analytics software such as
        # Google Analytics and Matomo.
        if token and 'unsub_token' in session:
            # Browser is okay with cookies. Do a 302 redirect
            # Strip out `cookietest=1` from the redirected URL
            return redirect(
                (
                    url_for('notification_unsubscribe_do')
                    + ('?' + request.query_string.decode())
                    if request.query_string
                    else ''
                )
                .replace('?cookietest=1&', '?')  # If cookietest is somehow at start
                .replace('?cookietest=1', '')  # Or if it's solo
                .replace('&cookietest=1', '')  # And/or if it's in the middle or end
            )

        # Step 4. We have a token and it's been stripped from the URL. Process it based
        # on the token type.
        if not token_type:
            token_type = session.get('unsub_token_type') or request.form['token_type']

        # --- Signed tokens (email)
        if token_type == 'signed':  # nosec
            try:
                # Token will be in session in the GET request, and in request.form
                # in the POST request because we'll move it over during the GET request.
                payload = token_serializer().loads(
                    session.get('unsub_token') or request.form['token'],
                    max_age=365 * 24 * 60 * 60,  # Validity 1 year (365 days)
                )
            except itsdangerous.SignatureExpired:
                # Link has expired. It's been over a year!
                session.pop('unsub_token', None)
                session.pop('unsub_token_type', None)
                flash(unsubscribe_link_expired, 'error')
                return redirect(url_for('notification_preferences'), code=303)
            except itsdangerous.BadData:
                session.pop('unsub_token', None)
                session.pop('unsub_token_type', None)
                flash(unsubscribe_link_invalid, 'error')
                return redirect(url_for('notification_preferences'), code=303)

        # --- Cached tokens (SMS)
        elif token_type == 'cached':  # nosec

            # Enforce a rate limit per IP on cached tokens, to slow down enumeration.
            # Some ISPs use carrier-grade NAT and will have a single IP for a very
            # large number of users, so we have generous limits. 100 unsubscribes per
            # 10 minutes (600s) per IP address.
            validate_rate_limit('sms_unsubscribe', str(request.remote_addr), 100, 600)

            payload = retrieve_cached_token(
                session.get('unsub_token') or request.form['token']
            )
            if not payload:
                # No payload, meaning invalid token
                session.pop('unsub_token', None)
                session.pop('unsub_token_type', None)
                flash(unsubscribe_link_invalid, 'error')
                return redirect(url_for('notification_preferences'), code=303)

            # Do `.replace(tzinfo=None)` on the datetime because -- while we use
            # naive timestamps when making the token -- there was a period of confusion
            # on whether the underlying cache supported both naive and aware datetimes.
            # (It does, because it stores Python pickles, not JSON.)
            if payload['timestamp'].replace(
                tzinfo=None
            ) < datetime.utcnow() - timedelta(days=7):
                # Link older than a week. Expire it
                session.pop('unsub_token', None)
                session.pop('unsub_token_type', None)
                flash(unsubscribe_link_expired, 'error')
                return redirect(url_for('notification_preferences'), code=303)

        else:
            # This is not supposed to happen
            abort(400)

        # Step 5. Validate whether the token matches the current user, if any
        # Do not allow links to be used across accounts.
        if current_auth.user and current_auth.user.buid != payload['buid']:
            return render_message(
                title=_("Unauthorized unsubscribe link"),
                message=_(
                    "This unsubscribe link is for someone else’s account. Please logout"
                    " or use an incognito/private browsing session to use this link"
                ),
            )

        # Step 6. Load the user. The contents of `payload` are defined in
        # :meth:`NotificationView.unsubscribe_token` above
        user = User.get(buid=payload['buid'])
        if user is None:
            app.logger.error(
                "Unsubscribe view cannot find user with buid %s", payload['buid']
            )
            return render_message(
                title=_("Unknown user account"),
                message=_("This unsubscribe link is for a non-existent user"),
            )
        if payload['transport'] == 'email' and 'hash' in payload:
            email_address = EmailAddress.get(email_hash=payload['hash'])
            if email_address is None:
                app.logger.error(
                    "Unsubscribe view cannot find email address with hash %s",
                    payload['hash'],
                )
            else:
                email_address.mark_active()
                db.session.commit()
        # TODO: Add active status for phone numbers and check here

        # Step 7. Ask the user to confirm unsubscribe. Do not unsubscribe on a GET
        # request as it may be triggered by link previews (for transports other than
        # email, or when an email is copy-pasted into a messenger app).
        form = UnsubscribeForm(
            obj=user,
            transport=payload['transport'],
            notification_type=payload['notification_type'],
        )
        # Move the token from session to form. The session is swept every 10 minutes,
        # so if the user opens an unsubscribe link, wanders away and comes back later,
        # it'll be gone from session. It's safe for longer in the form, and doesn't
        # bear the leakage risk of being in the URL where analytics software can log it.
        if 'unsub_token' in session:
            form.token.data = session.pop('unsub_token')
            form.token_type.data = session.pop('unsub_token_type')
        if form.validate_on_submit():
            form.populate_obj(user)
            db.session.commit()
            return render_message(
                title=_("Preferences saved"),
                message=_("Your notification preferences have been updated"),
            )
        return render_form(
            form=form,
            title=_("Notification preferences"),
            formid='unsubscribe-preferences',
            submit=_("Save preferences"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )


AccountNotificationView.init_app(app)
