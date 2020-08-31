from flask import current_app
from werkzeug.datastructures import MultiDict

import requests_mock

from funnel.forms import ProjectLivestreamForm


class TestProjectForms(object):
    def test_livestream_form_valid(self, test_client):
        with current_app.test_request_context('/'):
            with requests_mock.Mocker() as m:
                m.get("https://www.youtube.com/watch?v=dQw4w9WgXcQ", text='resp')
                form = ProjectLivestreamForm(
                    MultiDict(
                        {
                            'livestream_urls': "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                        }
                    ),
                    meta={'csrf': False},
                )
                assert form.validate()

                m.get("https://y2u.be/dQw4w9WgXcQ", text='resp')
                m.get("https://www.youtube.com/watch?v=dQw4w9WgXcQ", text='resp')
                m.get("https://youtu.be/dQw4w9WgXcQ", text='resp')
                m.get("https://vimeo.com/336892869", text='resp')
                m.get("https://www.vimeo.com/336892869", text='resp')
                form2 = ProjectLivestreamForm(
                    MultiDict(
                        {
                            'livestream_urls': """
                            https://y2u.be/dQw4w9WgXcQ
                            https://www.youtube.com/watch?v=dQw4w9WgXcQ
                            https://youtu.be/dQw4w9WgXcQ
                            https://vimeo.com/336892869
                            https://www.vimeo.com/336892869
                            """,
                        }
                    ),
                    meta={'csrf': False},
                )
                assert form2.validate()

    def test_livestream_form_invalid(self, test_client):
        with current_app.test_request_context('/'):
            with requests_mock.Mocker() as m:
                m.get("https://www.vimeo.com/336892869", text='resp')
                form = ProjectLivestreamForm(
                    MultiDict(
                        {
                            'livestream_urls': """
                            https://zoom.com/asdf
                            https://www.vimeo.com/336892869
                            """,
                        }
                    ),
                    meta={'csrf': False},
                )
                assert not form.validate()
