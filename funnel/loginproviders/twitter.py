"""Twitter OAuth1a client."""

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

    def do(self, callback_url):
        auth = tweepy.OAuthHandler(self.key, self.secret, callback_url)

        try:
            redirect_url = auth.get_authorization_url()
            return redirect(redirect_url)
        except tweepy.errors.TweepyException as exc:
            raise LoginInitError(
                _("Twitter had a temporary problem. Try again?")
            ) from exc

    def callback(self) -> LoginProviderData:
        auth = tweepy.OAuthHandler(self.key, self.secret)
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
        except tweepy.errors.TweepyException as exc:
            raise LoginCallbackError(
                _("Twitter had an intermittent problem. Try again?")
            ) from exc

        return LoginProviderData(
            email=getattr(twuser, 'email', None),
            userid=twuser.id_str,
            username=twuser.screen_name,
            fullname=twuser.name.strip() or '',
            avatar_url=twuser.profile_image_url_https,
            oauth_token=auth.access_token,
            oauth_token_secret=auth.access_token_secret,
        )
