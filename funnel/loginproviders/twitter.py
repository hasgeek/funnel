from __future__ import annotations

from flask import redirect, request

import tweepy

from baseframe import _

from ..registry import (
    LoginCallbackError,
    LoginInitError,
    LoginProvider,
    LoginProviderData,
)

__all__ = ['TwitterProvider']


class TwitterProvider(LoginProvider):
    at_username = True

    def __init__(
        self,
        name,
        title,
        key,
        secret,
        access_key,
        access_secret,
        at_login=True,
        priority=True,
        icon=None,
    ) -> None:
        self.name = name
        self.title = title
        self.at_login = at_login
        self.priority = priority
        self.icon = icon
        self.consumer_key = key
        self.consumer_secret = secret
        self.access_key = access_key
        self.access_secret = access_secret

    def do(self, callback_url):
        auth = tweepy.OAuthHandler(
            self.consumer_key, self.consumer_secret, callback_url
        )

        try:
            redirect_url = auth.get_authorization_url()
            return redirect(redirect_url)
        except tweepy.TweepError:
            raise LoginInitError(_("Twitter had a temporary problem. Try again?"))

    def callback(self) -> LoginProviderData:
        auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        request_token = request.args.get('oauth_token')
        request_verifier = request.args.get('oauth_verifier')

        if not request_token or not request_verifier:
            # No request token or verifier? Not a real callback then
            raise LoginCallbackError(
                _("Were you trying to login with Twitter? Try again to confirm")
            )

        auth.request_token = {
            'oauth_token': request_token,
            'oauth_token_secret': request_verifier,
        }

        try:
            auth.get_access_token(request_verifier)
            # Try to read more from the user's Twitter profile
            api = tweepy.API(auth)
            twuser = api.verify_credentials(
                include_entities='false', skip_status='true', include_email='true'
            )
        except tweepy.TweepError:
            raise LoginCallbackError(
                _("Twitter had an intermittent problem. Try again?")
            )

        return LoginProviderData(
            email=getattr(twuser, 'email', None),
            userid=twuser.id_str,
            username=twuser.screen_name,
            fullname=twuser.name.strip() or '',
            avatar_url=twuser.profile_image_url_https,
            oauth_token=auth.access_token,
            oauth_token_secret=auth.access_token_secret,
        )
