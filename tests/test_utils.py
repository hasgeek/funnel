# -*- coding: utf-8 -*-

from flask import current_app

from funnel.utils import (
    extract_twitter_handle,
    format_twitter_handle,
    geonameid_from_location,
    split_name,
)


class TestUtils(object):
    def test_extract_twitter_handle(self):
        expected = 'shreyas_satish'
        assert extract_twitter_handle('https://twitter.com/shreyas_satish') == expected
        assert (
            extract_twitter_handle('https://twitter.com/shreyas_satish/favorites')
            == expected
        )
        assert extract_twitter_handle('@shreyas_satish') == expected
        assert extract_twitter_handle('shreyas_satish') == expected
        assert extract_twitter_handle('seriouslylongstring') is None
        assert extract_twitter_handle('https://facebook.com/shreyas') is None
        assert extract_twitter_handle('') is None

    def test_geonameid_from_location(self, test_client):
        with current_app.test_request_context('/'):
            location = "Bangalore"
            expected_geonameid = 1277333
            assert expected_geonameid in geonameid_from_location(location)

    def test_split_name(self):
        assert split_name("ABC DEF EFG") == ("ABC", "DEF EFG")

    def test_format_twitter_handle(self):
        assert format_twitter_handle("testusername") == "@testusername"
