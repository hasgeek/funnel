import unittest

from funnel.utils import make_redirect_url, mask_email


class FlaskrTestCase(unittest.TestCase):
    def test_make_redirect_url(self):
        # scenario 1: straight forward splitting
        result = make_redirect_url('http://example.com/?foo=bar', foo='baz')
        expected_result = 'http://example.com/?foo=bar&foo=baz'
        self.assertEqual(result, expected_result)

        # scenario 2: with use_fragment set as True
        result = make_redirect_url(
            'http://example.com/?foo=bar', use_fragment=True, foo='baz'
        )
        expected_result = 'http://example.com/?foo=bar#foo=baz'
        self.assertEqual(result, expected_result)

    def test_mask_email(self):
        self.assertEqual(mask_email('foobar@example.com'), 'f****@e****')
