from __future__ import annotations

from base64 import b64encode

from flask import current_app, redirect, request, session

from furl import furl
from sentry_sdk import capture_exception
import requests
import simplejson

from baseframe import _

from ..registry import LoginCallbackError, LoginProvider, LoginProviderData

__all__ = ['ZoomProvider']


class ZoomProvider(LoginProvider):
    at_username = True
    auth_url = "https://zoom.us/oauth/authorize?response_type=code"  # nosec
    token_url = (
        "https://zoom.us/oauth/token?grant_type=authorization_code"  # nosec  # noqa
    )
    user_info = "https://api.zoom.us/v2/users/me"  # nosec

    def __init__(
        self, name, title, key, secret, at_login=False, priority=False, icon=None
    ) -> None:
        self.name = name
        self.title = title
        self.at_login = at_login
        self.priority = priority
        self.icon = icon

        self.key = key
        self.secret = secret

    def do(self, callback_url):
        session['oauth_callback'] = callback_url
        return redirect(
            furl(self.auth_url)
            .add(
                {
                    'client_id': self.key,
                    'redirect_uri': callback_url,
                }
            )
            .url
        )

    def callback(self) -> LoginProviderData:
        if request.args.get('error'):
            if request.args['error'] == 'user_denied':
                raise LoginCallbackError(_("You denied the Zoom login request"))
            elif request.args['error'] == 'redirect_uri_mismatch':
                # TODO: Log this as an exception for the server admin to look at
                raise LoginCallbackError(
                    _("This server's callback URL is misconfigured")
                )
            else:
                raise LoginCallbackError(_("Unknown failure"))
        code = request.args.get('code', None)
        try:
            response = requests.post(
                self.token_url,
                headers={
                    'Accept': 'application/x-www-form-urlencoded',
                    'Authorization': 'Basic '
                    + b64encode(f'{self.key}:{self.secret}'.encode()).decode('UTF-8'),
                },
                params={
                    'code': code,
                    'redirect_uri': session['oauth_callback'],
                },
            ).json()
            if 'error' in response:
                raise LoginCallbackError(response['error'])
            zoominfo = requests.get(
                self.user_info,
                timeout=30,
                headers={
                    "Authorization": "Bearer {token}".format(
                        token=response['access_token']
                    )
                },
            ).json()
        except (
            requests.exceptions.RequestException,
            simplejson.JSONDecodeError,
        ) as exc:
            current_app.logger.error("Zoom OAuth2 error: %s", repr(exc))
            capture_exception(exc)
            raise LoginCallbackError(_("Zoom had an intermittent problem. Try again?"))
        return LoginProviderData(
            email=zoominfo['email'],
            userid=zoominfo['id'],
            username=None,
            fullname=zoominfo.get('first_name') + ' ' + zoominfo.get('last_name'),
            avatar_url=None,
            oauth_token=response['access_token'],
            oauth_token_secret=None,  # OAuth 2 doesn't need token secrets
            oauth_token_type=response['token_type'],
            oauth_refresh_token=response['refresh_token'],
            oauth_expires_in=response['expires_in'],
        )
