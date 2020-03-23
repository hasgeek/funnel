# -*- coding: utf-8 -*-

import urllib.parse

import requests

from .. import redis_store
from . import db


class VideoMixin:
    video_id = db.Column(db.UnicodeText, nullable=True)
    video_source = db.Column(db.UnicodeText, nullable=True)

    @property
    def video(self):
        data = None
        if self.video_source:
            data = {
                'source': self.video_source,
                'id': self.video_id,
                'url': self.video_url,
                'thumbnail': self.thumbnail_url,
            }
        return data

    @property
    def video_url(self):
        if self.video_source:
            if self.video_source == 'youtube':
                return 'https://www.youtube.com/watch/?v={video_id}'.format(
                    video_id=self.video_id
                )
            elif self.video_source == 'vimeo':
                return 'https://vimeo.com/{video_id}'.format(video_id=self.video_id)
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
            if 'v' in queries and len(queries['v']) > 0:
                self.video_id = queries['v'][0]
                self.video_source = 'youtube'
            else:
                raise ValueError(
                    "YouTube video URLs need to be in the format: "
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                )
        elif parsed.netloc == 'youtu.be':
            video_id = parsed.path.lstrip('/')
            if video_id is not None:
                self.video_id = video_id
                self.video_source = 'youtube'
            else:
                raise ValueError(
                    "YouTube short URLs need to be in the format: "
                    "https://youtu.be/dQw4w9WgXcQ"
                )
        elif parsed.netloc in ['vimeo.com', 'www.vimeo.com']:
            video_id = parsed.path.lstrip('/')
            if video_id is not None:
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
                return '//www.youtube.com/embed/{video_id}?wmode=transparent&showinfo=0&rel=0&autohide=0&autoplay=0&enablejsapi=1&version=3'.format(
                    video_id=self.video_id
                )
            elif self.video_source == 'vimeo':
                return '//player.vimeo.com/video/{video_id}?api=1&player_id=vimeoplayer'.format(
                    video_id=self.video_id
                )
            elif self.video_source == 'raw':
                return self.video_id
        return None

    @property
    def thumbnail_key(self):
        if self.video_source and self.video_id:
            return self.video_source + "/" + self.video_id
        return None

    @property
    def thumbnail_url(self):
        if self.video_source:
            if self.video_source == 'youtube':
                return '//i.ytimg.com/vi/{video_id}/mqdefault.jpg'.format(
                    video_id=self.video_id
                )
            elif self.video_source == 'vimeo':
                cache_thumbnail_key = self.thumbnail_key
                cached_url = redis_store.get(cache_thumbnail_key)
                if cached_url is not None:
                    return cached_url
                else:
                    vimeo_video = requests.get(
                        "https://vimeo.com/api/v2/video/%s.json" % (self.video_id)
                    ).json()
                    if len(vimeo_video) > 0:
                        thumbnail_medium = vimeo_video[0]['thumbnail_medium']
                        redis_store.set(cache_thumbnail_key, thumbnail_medium)
                        return thumbnail_medium
        return None
