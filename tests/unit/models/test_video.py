# -*- coding: utf-8 -*-

from datetime import datetime

from coaster.utils import parse_isoformat
from funnel import redis_store
from funnel.models import Proposal


class TestLabels(object):
    def test_main_label_from_fixture(self, test_client, test_db, new_proposal):
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
        assert check_proposal.video['source'] == check_proposal.video_source
        assert check_proposal.video['id'] == check_proposal.video_id
        assert check_proposal.video['url'] == check_proposal.video_url
        assert check_proposal.video['duration'] == 213
        assert check_proposal.video['uploaded_at'] == datetime(2009, 10, 25, 1, 27, 33)
        assert (
            check_proposal.video['thumbnail']
            == f'https://i.ytimg.com/vi/{check_proposal.video_id}/mqdefault.jpg'
        )

        # let's try to check the cache directly
        check_cached = redis_store.hgetall(check_proposal.video_cache_key)
        assert check_cached is not None
        assert check_cached['source'] == check_proposal.video_source
        assert check_cached['id'] == check_proposal.video_id
        assert check_cached['url'] == check_proposal.video_url
        assert int(check_cached['duration']) == 213
        assert parse_isoformat(check_cached['uploaded_at']) == datetime(
            2009, 10, 25, 1, 27, 33
        )
        assert (
            check_cached['thumbnail']
            == f'https://i.ytimg.com/vi/{check_proposal.video_id}/mqdefault.jpg'
        )
