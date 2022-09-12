"""Tests for Project forms."""
# pylint: disable=import-outside-toplevel

from werkzeug.datastructures import MultiDict

import pytest
import requests_mock


@pytest.mark.usefixtures('app_context')
def test_livestream_form_valid(forms) -> None:
    with requests_mock.Mocker() as m:
        valid_urls = [
            "https://y2u.be/dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://vimeo.com/336892869",
            "https://www.vimeo.com/336892869",
        ]

        for url in valid_urls:
            m.get(url, text='resp')

        # Single url
        form = forms.ProjectLivestreamForm(
            MultiDict({'livestream_urls': valid_urls[0]}), meta={'csrf': False}
        )
        assert form.validate()

        # Multiple urls in multiple lines
        form2 = forms.ProjectLivestreamForm(
            MultiDict({'livestream_urls': '\n'.join(valid_urls)}),
            meta={'csrf': False},
        )
        assert form2.validate()


@pytest.mark.usefixtures('app_context')
def test_livestream_form_invalid(forms) -> None:
    with requests_mock.Mocker() as m:
        m.get("https://www.vimeo.com/336892869", text='resp')
        form = forms.ProjectLivestreamForm(
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
