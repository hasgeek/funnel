"""Zoom OAuth2 client."""

from __future__ import annotations

from base64 import b64encode

import requests
from flask import current_app, redirect, request, session
from furl import furl
from sentry_sdk import capture_exception

from baseframe import _

from ..registry import LoginCallbackError, LoginProvider, LoginProviderData

__all__ = ['ZoomProvider']


class ZoomProvider(LoginProvider):
    at_username = False
    auth_url = 'https://zoom.us/oauth/authorize?response_type=code'  # nosec
    token_url = 'https://zoom.us/oauth/token?grant_type=authorization_code'  # nosec
    user_info_url = 'https://api.zoom.us/v2/users/me'  # nosec

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
            if request.args['error'] == 'redirect_uri_mismatch':
                current_app.logger.error(
                    "Zoom callback URL is misconfigured. Response: %r",
                    dict(request.args),
                )
                raise LoginCallbackError(
                    _("This server’s callback URL is misconfigured")
                )
            raise LoginCallbackError(_("Unknown failure"))
        code = request.args.get('code', None)
        try:
            response = requests.post(
                self.token_url,
                timeout=30,
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
                self.user_info_url,
                timeout=30,
                headers={'Authorization': f'Bearer {response["access_token"]}'},
            ).json()
        except (
            requests.exceptions.RequestException,
            requests.exceptions.JSONDecodeError,
        ) as exc:
            current_app.logger.error("Zoom OAuth2 error: %s", repr(exc))
            capture_exception(exc)
            raise LoginCallbackError(
                _("Zoom had an intermittent problem. Try again?")
            ) from exc
        return LoginProviderData(
            email=zoominfo['email'],
            emails=[zoominfo['email']],
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
