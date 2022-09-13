"""Test embedded video view helpers."""

from datetime import datetime
import logging

from pytz import utc
import pytest
import requests

from funnel import models


def test_parse_video_url() -> None:
    assert models.parse_video_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ') == (
        'youtube',
        'dQw4w9WgXcQ',
    )
    assert models.parse_video_url('https://vimeo.com/336892869') == (
        'vimeo',
        '336892869',
    )
    assert models.parse_video_url(
        'https://drive.google.com/open?id=1rwHdWYnF4asdhsnDwLECoqZQy4o'
    ) == ('googledrive', '1rwHdWYnF4asdhsnDwLECoqZQy4o')
    assert models.parse_video_url(
        'https://drive.google.com/file/d/1rwHdWYnF4asdhsnDwLECoqZQy4o/view'
    ) == ('googledrive', '1rwHdWYnF4asdhsnDwLECoqZQy4o')


def test_youtube_video_delete(db_session, new_proposal) -> None:
    assert new_proposal.title == "Test Proposal"

    new_proposal.video_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    db_session.commit()

    assert new_proposal.video_source == 'youtube'
    assert new_proposal.video_id == 'dQw4w9WgXcQ'

    new_proposal.video_url = None
    db_session.commit()

    assert new_proposal.video_source is None
    assert new_proposal.video_id is None


@pytest.mark.remote_data()
@pytest.mark.requires_config('youtube')
@pytest.mark.usefixtures('app_context')
def test_youtube(db_session, new_proposal) -> None:
    assert new_proposal.title == "Test Proposal"

    new_proposal.video_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    db_session.commit()

    check_proposal = models.Proposal.query.filter_by(id=new_proposal.id).first()
    assert check_proposal is not None
    assert check_proposal.video_source == 'youtube'
    assert check_proposal.video_id == 'dQw4w9WgXcQ'
    assert check_proposal.video_url == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    # the first returned value of .video will be calculated values
    # and then it'll cache everything in redis
    check_video = check_proposal.views.video
    assert check_video['source'] == check_proposal.video_source
    assert check_video['id'] == check_proposal.video_id
    assert check_video['url'] == check_proposal.video_url
    assert check_video['duration'] == 213
    assert check_video['uploaded_at'] == utc.localize(datetime(2009, 10, 25, 6, 57, 33))
    assert (
        check_video['thumbnail']
        == f'https://i.ytimg.com/vi/{check_proposal.video_id}/mqdefault.jpg'
    )


def test_vimeo_video_delete(db_session, new_proposal) -> None:
    assert new_proposal.title == "Test Proposal"

    new_proposal.video_url = 'https://vimeo.com/336892869'
    db_session.commit()

    assert new_proposal.video_source == 'vimeo'
    assert new_proposal.video_id == '336892869'

    new_proposal.video_url = None
    db_session.commit()

    assert new_proposal.video_source is None
    assert new_proposal.video_id is None


@pytest.mark.remote_data()
@pytest.mark.requires_config('vimeo')
@pytest.mark.usefixtures('app_context')
def test_vimeo(db_session, new_proposal) -> None:
    assert new_proposal.title == "Test Proposal"

    new_proposal.video_url = 'https://vimeo.com/336892869'
    db_session.commit()

    check_proposal = models.Proposal.query.filter_by(id=new_proposal.id).first()
    assert check_proposal is not None
    assert check_proposal.video_source == 'vimeo'
    assert check_proposal.video_id == '336892869'
    assert check_proposal.video_url == 'https://vimeo.com/336892869'

    # the first returned value of .video will be calculated values
    # and then it'll cache everything in redis
    check_video = check_proposal.views.video
    assert check_video['source'] == check_proposal.video_source
    assert check_video['id'] == check_proposal.video_id
    assert check_video['url'] == check_proposal.video_url
    assert check_video['duration'] == 212
    assert check_video['uploaded_at'] == utc.localize(datetime(2019, 5, 17, 19, 48, 2))
    assert check_video['thumbnail'].startswith('https://i.vimeocdn.com/video/783856813')


@pytest.mark.requires_config('vimeo')
@pytest.mark.usefixtures('app_context')
def test_vimeo_request_exception(caplog, requests_mock, new_proposal):
    caplog.set_level(logging.WARNING)
    requests_mock.get(
        'https://api.vimeo.com/videos/336892869',
        exc=requests.exceptions.RequestException,
    )
    new_proposal.video_url = 'https://vimeo.com/336892869'
    assert new_proposal.views.video is not None
    assert "Vimeo API request error: RequestException()" in caplog.text


@pytest.mark.usefixtures('app_context')
def test_youtube_request_exception(caplog, requests_mock, new_proposal):
    caplog.set_level(logging.WARNING)
    requests_mock.get(
        'https://www.googleapis.com/youtube/v3/videos',
        exc=requests.exceptions.RequestException,
    )
    new_proposal.video_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    assert new_proposal.views.video is not None
    assert "YouTube API request error: RequestException()" in caplog.text
