from __future__ import annotations

from flask import current_app, redirect, request

from furl import furl
from sentry_sdk import capture_exception
import requests
import simplejson

from baseframe import _

from ..registry import LoginCallbackError, LoginProvider, LoginProviderData

__all__ = ['GitHubProvider']


class GitHubProvider(LoginProvider):
    at_username = True
    auth_url = 'https://github.com/login/oauth/authorize'
    token_url = 'https://github.com/login/oauth/access_token'  # nosec
    user_info = 'https://api.github.com/user'
    user_emails = 'https://api.github.com/user/emails'

    def __init__(
        self, name, title, key, secret, at_login=True, priority=False, icon=None
    ) -> None:
        self.name = name
        self.title = title
        self.at_login = at_login
        self.priority = priority
        self.icon = icon

        self.key = key
        self.secret = secret

    def do(self, callback_url):
        return redirect(
            furl(self.auth_url)
            .add(
                {
                    'client_id': self.key,
                    'redirect_uri': callback_url,
                    'scope': 'user:email',
                }
            )
            .url
        )

    def callback(self) -> LoginProviderData:
        if request.args.get('error'):
            if request.args['error'] == 'user_denied':
                raise LoginCallbackError(_("You denied the GitHub login request"))
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
                headers={'Accept': 'application/json'},
                params={
                    'client_id': self.key,
                    'client_secret': self.secret,
                    'code': code,
                },
            ).json()
            if 'error' in response:
                raise LoginCallbackError(response['error'])
            ghinfo = requests.get(
                self.user_info,
                timeout=30,
                headers={
                    "Authorization": "token {token}".format(
                        token=response['access_token']
                    )
                },
            ).json()
            ghemails = requests.get(
                self.user_emails,
                timeout=30,
                headers={
                    'Accept': 'application/vnd.github.v3+json',
                    "Authorization": "token {token}".format(
                        token=response['access_token']
                    ),
                },
            ).json()
        except (
            requests.exceptions.RequestException,
            simplejson.JSONDecodeError,
        ) as exc:
            current_app.logger.error("GitHub OAuth2 error: %s", repr(exc))
            capture_exception(exc)
            raise LoginCallbackError(
                _("GitHub had an intermittent problem. Try again?")
            )

        email = None
        emails = []
        if ghemails and isinstance(ghemails, (list, tuple)):
            for result in ghemails:
                if result.get('verified') and not result['email'].endswith(
                    '@users.noreply.github.com'
                ):
                    emails.append(result['email'])
        if emails:
            email = emails[0]
        return LoginProviderData(
            email=email,
            emails=emails,
            userid=ghinfo['login'],
            username=ghinfo['login'],
            fullname=(ghinfo.get('name') or '').strip(),
            avatar_url=ghinfo.get('avatar_url'),
            oauth_token=response['access_token'],
            oauth_token_type=response['token_type'],
        )
