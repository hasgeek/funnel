# -*- coding: utf-8 -*-
import unittest
from funnel.util import format_twitter_handle


class TestUtils(unittest.TestCase):
    def test_format_twitter_handle(self):
        expected = u'shreyas_satish'
        self.assertEquals(format_twitter_handle('https://twitter.com/shreyas_satish'), expected)
        self.assertEquals(format_twitter_handle('https://twitter.com/shreyas_satish/favorites'), expected)
        self.assertEquals(format_twitter_handle('@shreyas_satish'), expected)
        self.assertEquals(format_twitter_handle('shreyas_satish'), expected)
        self.assertEquals(format_twitter_handle('seriouslylongstring'), None)
        self.assertEquals(format_twitter_handle('https://facebook.com/shreyas'), None)
        self.assertEquals(format_twitter_handle(''), None)
