# -*- coding: utf-8 -*-

import urllib.parse

from pytz import UTC
import requests

from coaster.utils import parse_duration, parse_isoformat

from .. import app, redis_store
from . import db


class VideoException(Exception):
    pass


class VideoMixin:
    video_id = db.Column(db.UnicodeText, nullable=True)
    video_source = db.Column(db.UnicodeText, nullable=True)

    @property
    def video_cache_key(self):
        if self.video_source and self.video_id:
            return 'video_cache/' + self.video_source + '/' + self.video_id
        else:
            raise VideoException("No video source or ID to create a cache key")

    @property
    def _video_cache(self):
        data = redis_store.hgetall(self.video_cache_key)
        if data:
            if 'uploaded_at' in data:
                data['uploaded_at'] = parse_isoformat(data['uploaded_at'], naive=False)
            if 'duration' in data:
                data['duration'] = int(data['duration'])
        return data

    @_video_cache.setter
    def _video_cache(self, data):
        copied_data = data.copy()
        copied_data['uploaded_at'] = copied_data['uploaded_at'].isoformat()
        if copied_data['duration'] and not isinstance(copied_data['duration'], int):
            copied_data['duration'] = int(copied_data['duration'])
        redis_store.hmset(self.video_cache_key, copied_data)
        redis_store.expire(self.video_cache_key, 60 * 60 * 24 * 2)  # caching for 2 days

    @property
    def video(self):
        data = None
        if self.video_source and self.video_id:
            data = self._video_cache

            if not data:
                data = {
                    'source': self.video_source,
                    'id': self.video_id,
                    'url': self.video_url,
                }
                if self.video_source == 'youtube':
                    youtube_video = requests.get(
                        f'https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id={self.video_id}&key={app.config["YOUTUBE_API_KEY"]}'
                    ).json()
                    if (
                        not youtube_video
                        or 'items' not in youtube_video
                        or not youtube_video['items']
                    ):
                        raise VideoException(
                            "Unable to fetch data, please check the youtube url or API key"
                        )
                    else:
                        youtube_video = youtube_video['items'][0]

                        data['duration'] = parse_duration(
                            youtube_video['contentDetails']['duration']
                        ).total_seconds()
                        data['uploaded_at'] = parse_isoformat(
                            youtube_video['snippet']['publishedAt'], naive=False
                        )
                        data['thumbnail'] = youtube_video['snippet']['thumbnails'][
                            'medium'
                        ]['url']
                elif self.video_source == 'vimeo':
                    vimeo_video = requests.get(
                        f'https://vimeo.com/api/v2/video/{self.video_id}.json'
                    ).json()
                    if not vimeo_video:
                        raise VideoException(
                            "Unable to fetch data, please check the vimeo url"
                        )
                    else:
                        vimeo_video = vimeo_video[0]

                        data['duration'] = vimeo_video['duration']
                        # Vimeo returns naive datetime, we will add UTC timezone to it
                        data['uploaded_at'] = parse_isoformat(
                            vimeo_video['upload_date'], delimiter=' '
                        ).replace(tzinfo=UTC)
                        data['thumbnail'] = vimeo_video['thumbnail_medium']
                else:
                    # source = raw
                    data['duration'] = 0
                    data['uploaded_at'] = None
                    data['thumbnail'] = None
                self._video_cache = data  # using _video_cache setter to set cache
        return data

    @property
    def video_url(self):
        if self.video_source:
            if self.video_source == 'youtube':
                return f'https://www.youtube.com/watch?v={self.video_id}'
            elif self.video_source == 'vimeo':
                return f'https://vimeo.com/{self.video_id}'
            elif self.video_source == 'raw':
                return self.video_id
        return None

    @video_url.setter
    def video_url(self, value):
        parsed = urllib.parse.urlparse(value)
        if parsed.netloc is None:
            raise ValueError("Invalid video URL")

        if parsed.netloc in ['youtube.com', 'www.youtube.com']:
            queries = urllib.parse.parse_qs(parsed.query)
            if 'v' in queries and queries['v']:
                self.video_id = queries['v'][0]
                self.video_source = 'youtube'
            else:
                raise ValueError(
                    "YouTube video URLs need to be in the format: "
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                )
        elif parsed.netloc == 'youtu.be':
            video_id = parsed.path.lstrip('/')
            if video_id:
                self.video_id = video_id
                self.video_source = 'youtube'
            else:
                raise ValueError(
                    "YouTube short URLs need to be in the format: "
                    "https://youtu.be/dQw4w9WgXcQ"
                )
        elif parsed.netloc in ['vimeo.com', 'www.vimeo.com']:
            video_id = parsed.path.lstrip('/')
            if video_id:
                self.video_id = video_id
                self.video_source = 'vimeo'
            else:
                raise ValueError(
                    "Vimeo video URLs need to be in the format: "
                    "https://vimeo.com/336892869"
                )
        else:
            self.video_source = 'raw'
            self.video_id = value

    @property
    def embeddable_video_url(self):
        if self.video_source:
            if self.video_source == 'youtube':
                return f'https://www.youtube.com/embed/{self.video_id}?wmode=transparent&showinfo=0&rel=0&autohide=0&autoplay=0&enablejsapi=1&version=3'
            elif self.video_source == 'vimeo':
                return f'https://player.vimeo.com/video/{self.video_id}?api=1&player_id=vimeoplayer'
            elif self.video_source == 'raw':
                return self.video_id
        return None
