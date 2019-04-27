# -*- coding: utf-8 -*-

from flask import current_app
from werkzeug.datastructures import MultiDict
from funnel.forms import LabelForm


class TestLabelForms(object):
    def test_label_form(self, test_client):
        with current_app.test_request_context('/'):
            form = LabelForm(MultiDict({
                'title': u"Test label title",
                'icon_emoji': u"🔟",
                'required': False,
                'restricted': False
            }), meta={'csrf': False})
            assert form.validate()

    def test_label_form_invalid(self, test_client):
        with current_app.test_request_context('/'):
            form = LabelForm(MultiDict({
                'icon_emoji': u"🔟",
                'required': False,
                'restricted': False
            }), meta={'csrf': False})
            # title is required
            assert not form.validate()
