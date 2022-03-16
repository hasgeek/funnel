from __future__ import annotations

from baseframe import __

from ..registry import login_registry
from .github import GitHubProvider
from .google import GoogleProvider
from .linkedin import LinkedInProvider
from .twitter import TwitterProvider
from .zoom import ZoomProvider


def init_app(app):
    # Register some login providers
    if app.config.get('OAUTH_GOOGLE_KEY') and app.config.get('OAUTH_GOOGLE_SECRET'):
        login_registry['google'] = GoogleProvider(
            'google',
            __("Google"),
            client_id=app.config['OAUTH_GOOGLE_KEY'],
            secret=app.config['OAUTH_GOOGLE_SECRET'],
            scope=app.config.get('OAUTH_GOOGLE_SCOPE', ['email', 'profile']),
            at_login=True,
            priority=True,
            icon='google',
        )
    if app.config.get('OAUTH_TWITTER_KEY') and app.config.get('OAUTH_TWITTER_SECRET'):
        login_registry['twitter'] = TwitterProvider(
            'twitter',
            __("Twitter"),
            at_login=True,
            priority=True,
            icon='twitter',
            key=app.config['OAUTH_TWITTER_KEY'],
            secret=app.config['OAUTH_TWITTER_SECRET'],
            access_key=app.config.get('OAUTH_TWITTER_ACCESS_KEY'),
            access_secret=app.config.get('OAUTH_TWITTER_ACCESS_SECRET'),
        )
    if app.config.get('OAUTH_LINKEDIN_KEY') and app.config.get('OAUTH_LINKEDIN_SECRET'):
        login_registry['linkedin'] = LinkedInProvider(
            'linkedin',
            __("LinkedIn"),
            at_login=True,
            priority=False,
            icon='linkedin',
            key=app.config['OAUTH_LINKEDIN_KEY'],
            secret=app.config['OAUTH_LINKEDIN_SECRET'],
        )
    if app.config.get('OAUTH_GITHUB_KEY') and app.config.get('OAUTH_GITHUB_SECRET'):
        login_registry['github'] = GitHubProvider(
            'github',
            __("GitHub"),
            at_login=True,
            priority=False,
            icon='github',
            key=app.config['OAUTH_GITHUB_KEY'],
            secret=app.config['OAUTH_GITHUB_SECRET'],
        )
    if app.config.get('OAUTH_ZOOM_KEY') and app.config.get('OAUTH_ZOOM_SECRET'):
        login_registry['zoom'] = ZoomProvider(
            'zoom',
            __("Zoom"),
            at_login=False,
            priority=False,
            icon='zoom',
            key=app.config['OAUTH_ZOOM_KEY'],
            secret=app.config['OAUTH_ZOOM_SECRET'],
        )
