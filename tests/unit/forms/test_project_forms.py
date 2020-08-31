from flask import current_app
from werkzeug.datastructures import MultiDict

from funnel.forms import ProjectLivestreamForm


class TestProjectForms(object):
    def test_livestream_form_valid(self, test_client):
        with current_app.test_request_context('/'):
            form = ProjectLivestreamForm(
                MultiDict(
                    {'livestream_urls': "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
                ),
                meta={'csrf': False},
            )
            assert form.validate()

            form2 = ProjectLivestreamForm(
                MultiDict(
                    {
                        'livestream_urls': """
                        https://y2u.be/dQw4w9WgXcQ
                        https://www.youtube.com/watch?v=dQw4w9WgXcQ
                        https://youtu.be/dQw4w9WgXcQ
                        https://www.vimeo.com/336892869
                        https://www.vimeo.com/336892869
                        """,
                    }
                ),
                meta={'csrf': False},
            )
            assert form2.validate()

    def test_livestream_form_invalid(self, test_client):
        with current_app.test_request_context('/'):
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
