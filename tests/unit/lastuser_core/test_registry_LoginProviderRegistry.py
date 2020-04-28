# -*- coding: utf-8 -*-

import unittest

from funnel import app
from funnel.registry import LoginProviderRegistry, login_registry


class TestLoginProviderRegistry(unittest.TestCase):
    def test_loginproviderregistry(self):
        """
        Test for verifying creation of LoginProviderRegistry
        instance.
        """
        # A LoginProviderRegistry instance is created (based on
        # configuration provided) when init_for is called during
        # creation of app instance. To test and verify this correctly
        # we temporarily do not use the app instance available globally
        # and construct app instance separately
        expected_login_providers = []
        if app.config.get('OAUTH_TWITTER_KEY') and app.config.get(
            'OAUTH_TWITTER_SECRET'
        ):
            expected_login_providers.append('twitter')
        if app.config.get('OAUTH_GOOGLE_KEY') and app.config.get('OAUTH_GOOGLE_SECRET'):
            expected_login_providers.append('google')
        if app.config.get('OAUTH_LINKEDIN_KEY') and app.config.get(
            'OAUTH_LINKEDIN_SECRET'
        ):
            expected_login_providers.append('linkedin')
        if app.config.get('OAUTH_GITHUB_KEY') and app.config.get('OAUTH_GITHUB_SECRET'):
            expected_login_providers.append('github')

        assert isinstance(login_registry, LoginProviderRegistry)
        assert expected_login_providers == list(login_registry.keys())
