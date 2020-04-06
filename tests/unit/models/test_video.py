# -*- coding: utf-8 -*-

from datetime import datetime

from pytz import UTC

from funnel import redis_store
from funnel.models import Proposal


class TestVideos(object):
    def test_youtube(self, test_client, test_db, new_proposal):
        assert new_proposal.title == "Test Proposal"

        new_proposal.video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        test_db.session.commit()

        check_proposal = Proposal.query.filter_by(id=new_proposal.id).first()
        assert check_proposal is not None
        assert check_proposal.video_source == "youtube"
        assert check_proposal.video_id == "dQw4w9WgXcQ"
        assert check_proposal.video_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # delete existing cache if any
        redis_store.hdel(
            check_proposal.video_cache_key,
            'source',
            'id',
            'url',
            'duration',
            'thumbnail',
            'uploaded_at',
        )

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
