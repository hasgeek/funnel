from datetime import datetime

from pytz import UTC

from funnel.models import Proposal
from funnel.models.video import parse_video_url


class TestVideos(object):
    def test_parse_video_url(self):
        assert parse_video_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ') == (
            'youtube',
            'dQw4w9WgXcQ',
        )
        assert parse_video_url('https://vimeo.com/336892869') == ('vimeo', '336892869')
        assert parse_video_url(
            'https://drive.google.com/open?id=1rwHdWYnF4asdhsnDwLECoqZQy4o'
        ) == ('googledrive', '1rwHdWYnF4asdhsnDwLECoqZQy4o')
        assert parse_video_url(
            'https://drive.google.com/file/d/1rwHdWYnF4asdhsnDwLECoqZQy4o/view'
        ) == ('googledrive', '1rwHdWYnF4asdhsnDwLECoqZQy4o')

    def test_youtube_video_delete(self, test_db, new_proposal):
        assert new_proposal.title == "Test Proposal"

        new_proposal.video_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        test_db.session.commit()

        assert new_proposal.video_source == 'youtube'
        assert new_proposal.video_id == 'dQw4w9WgXcQ'

        new_proposal.video_url = None
        test_db.session.commit()

        assert new_proposal.video_source is None
        assert new_proposal.video_id is None

    def test_youtube(self, test_db, new_proposal):
        assert new_proposal.title == "Test Proposal"

        new_proposal.video_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        test_db.session.commit()

        check_proposal = Proposal.query.filter_by(id=new_proposal.id).first()
        assert check_proposal is not None
        assert check_proposal.video_source == 'youtube'
        assert check_proposal.video_id == 'dQw4w9WgXcQ'
        assert check_proposal.video_url == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

        # the first returned value of .video will be calculated values
        # and then it'll cache everything in redis
        check_video = check_proposal.video
        assert check_video['source'] == check_proposal.video_source
        assert check_video['id'] == check_proposal.video_id
        assert check_video['url'] == check_proposal.video_url
        assert check_video['duration'] == 213
        assert check_video['uploaded_at'] == datetime(
            2009, 10, 25, 6, 57, 33, tzinfo=UTC
        )
        assert (
            check_video['thumbnail']
            == f'https://i.ytimg.com/vi/{check_proposal.video_id}/mqdefault.jpg'
        )

        # let's try to check the cache directly
        check_cached = check_proposal._video_cache
        assert check_cached is not None
        assert check_cached['source'] == check_proposal.video_source
        assert check_cached['id'] == check_proposal.video_id
        assert check_cached['url'] == check_proposal.video_url
        assert check_cached['duration'] == 213
        assert check_cached['uploaded_at'] == datetime(
            2009, 10, 25, 6, 57, 33, tzinfo=UTC
        )
        assert (
            check_cached['thumbnail']
            == f'https://i.ytimg.com/vi/{check_proposal.video_id}/mqdefault.jpg'
        )

    def test_vimeo_video_delete(self, test_db, new_proposal):
        assert new_proposal.title == "Test Proposal"

        new_proposal.video_url = 'https://vimeo.com/336892869'
        test_db.session.commit()

        assert new_proposal.video_source == 'vimeo'
        assert new_proposal.video_id == '336892869'

        new_proposal.video_url = None
        test_db.session.commit()

        assert new_proposal.video_source is None
        assert new_proposal.video_id is None

    def test_vimeo(self, test_db, new_proposal):
        assert new_proposal.title == "Test Proposal"

        new_proposal.video_url = 'https://vimeo.com/336892869'
        test_db.session.commit()

        check_proposal = Proposal.query.filter_by(id=new_proposal.id).first()
        assert check_proposal is not None
        assert check_proposal.video_source == 'vimeo'
        assert check_proposal.video_id == '336892869'
        assert check_proposal.video_url == 'https://vimeo.com/336892869'

        # the first returned value of .video will be calculated values
        # and then it'll cache everything in redis
        check_video = check_proposal.video
        assert check_video['source'] == check_proposal.video_source
        assert check_video['id'] == check_proposal.video_id
        assert check_video['url'] == check_proposal.video_url
        assert check_video['duration'] == 212
        assert check_video['uploaded_at'] == datetime(
            2019, 5, 17, 15, 48, 2, tzinfo=UTC
        )
        assert (
            check_video['thumbnail']
            == 'https://i.vimeocdn.com/video/783856813_200x150.jpg'
        )

        # let's try to check the cache directly
        check_cached = check_proposal._video_cache
        assert check_cached is not None
        assert check_cached['source'] == check_proposal.video_source
        assert check_cached['id'] == check_proposal.video_id
        assert check_cached['url'] == check_proposal.video_url
        assert check_cached['duration'] == 212
        assert check_cached['uploaded_at'] == datetime(
            2019, 5, 17, 15, 48, 2, tzinfo=UTC
        )
        assert (
            check_cached['thumbnail']
            == 'https://i.vimeocdn.com/video/783856813_200x150.jpg'
        )
