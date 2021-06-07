from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Tuple, Union, cast
import urllib.parse

from flask import current_app

from pytz import utc
from simplejson import JSONDecodeError
import requests
import vimeo

from coaster.utils import parse_duration, parse_isoformat

from .. import app, redis_store
from . import db


class VideoException(Exception):
    pass


def parse_video_url(video_url: str) -> Tuple[str, str]:
    video_source = 'raw'
    video_id = video_url

    parsed = urllib.parse.urlparse(video_url)
    if parsed.netloc is None:
        raise ValueError("Invalid video URL")

    if parsed.netloc in ['youtube.com', 'www.youtube.com', 'm.youtube.com']:
        if parsed.path == '/watch':
            queries = urllib.parse.parse_qs(parsed.query)
            if 'v' in queries and queries['v']:
                video_id = queries['v'][0]
                video_source = 'youtube'
            else:
                raise ValueError(
                    f"{video_url}: YouTube video URLs need to be in the format:"
                    " https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                )
        elif parsed.path.startswith('/embed'):
            video_id = parsed.path.lstrip('/embed/')
            if video_id:
                video_source = 'youtube'
            else:
                raise ValueError(
                    f"{video_url}: YouTube video URLs need to be in the format:"
                    " https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                )
        else:
            raise ValueError(
                f"{video_url}: YouTube video URLs need to be in the format:"
                " https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )
    elif parsed.netloc == 'youtu.be':
        video_id = parsed.path.lstrip('/')
        if video_id:
            video_source = 'youtube'
        else:
            raise ValueError(
                "YouTube short URLs need to be in the format:"
                " https://youtu.be/dQw4w9WgXcQ"
            )
    elif parsed.netloc in ['vimeo.com', 'www.vimeo.com']:
        video_id = parsed.path.lstrip('/')
        if video_id:
            video_source = 'vimeo'
        else:
            raise ValueError(
                "Vimeo video URLs need to be in the format:"
                " https://vimeo.com/336892869"
            )
    elif parsed.netloc == 'drive.google.com':
        if parsed.path.startswith('/open'):
            queries = urllib.parse.parse_qs(parsed.query)
            if 'id' in queries and queries['id']:
                video_id = queries['id'][0]
                video_source = 'googledrive'
            else:
                raise ValueError(
                    f"{video_url}: Google drive video URLs need to be in the format:"
                    " https://drive.google.com/open?id=1rwHdWYnF4asdhsnDwLECoqZQy4o or"
                    " https://drive.google.com/file/d/1rwHdWYnF4asdhsnDwLECoqZQy4o/view"
                )
        elif parsed.path.startswith('/file/d/'):
            video_id = parsed.path.lstrip('/file/d/').rstrip('/view').rstrip('/preview')
            video_source = 'googledrive'
        else:
            raise ValueError(
                f"{video_url}: Google drive video URLs need to be in the format:"
                " https://drive.google.com/open?id=1rwHdWYnF4asdhsnDwLECoqZQy4o or"
                " https://drive.google.com/file/d/1rwHdWYnF4asdhsnDwLECoqZQy4o/view"
            )
    return video_source, video_id


def make_video_url(video_source: str, video_id: str) -> str:
    if video_source == 'youtube':
        return f'https://www.youtube.com/watch?v={video_id}'
    elif video_source == 'vimeo':
        return f'https://vimeo.com/{video_id}'
    elif video_source == 'googledrive':
        return f'https://drive.google.com/file/d/{video_id}/view'
    elif video_source == 'raw':
        return video_id
    raise ValueError("Unknown video source")


class VideoMixin:
    video_id: db.Column = db.Column(db.UnicodeText, nullable=True)
    video_source: db.Column = db.Column(db.UnicodeText, nullable=True)

    # We'll assume that the video exists at the source.
    # We'll get to know whether it actually exists when
    # we make API calls for thumbnails etc.
    _source_video_exists = True

    @property
    def video_cache_key(self) -> str:
        if self.video_source and self.video_id:
            return 'video_cache/' + self.video_source + '/' + self.video_id
        raise VideoException("No video source or ID to create a cache key")

    @property
    def _video_cache(self) -> Dict[str, Union[str, float, datetime]]:
        data = redis_store.hgetall(self.video_cache_key)
        if data:
            if 'uploaded_at' in data and data['uploaded_at']:
                data['uploaded_at'] = parse_isoformat(data['uploaded_at'], naive=False)
            if 'duration' in data and data['duration']:
                data['duration'] = float(data['duration'])
        return data

    @_video_cache.setter
    def _video_cache(self, data: dict):
        copied_data = data.copy()
        if copied_data['uploaded_at']:
            copied_data['uploaded_at'] = copied_data['uploaded_at'].isoformat()
        if copied_data['duration'] and not isinstance(copied_data['duration'], float):
            copied_data['duration'] = float(copied_data['duration'])
        redis_store.hmset(self.video_cache_key, copied_data)

        # if video exists at source, cache for 2 days, if not, for 6 hours
        hours_to_cache = 2 * 24 if self._source_video_exists else 6
        redis_store.expire(self.video_cache_key, 60 * 60 * hours_to_cache)

    # TODO: Create a dataclass for data

    @property
    def video_url(self) -> Optional[str]:
        if self.video_source and self.video_id:
            return make_video_url(self.video_source, self.video_id)
        return None

    @video_url.setter
    def video_url(self, value: str):
        if not value:
            if (
                self.video_id
                and self.video_source
                and redis_store.exists(self.video_cache_key)
            ):
                redis_store.delete(self.video_cache_key)
            self.video_source, self.video_id = None, None
        else:
            self.video_source, self.video_id = parse_video_url(value)

    @property
    def embeddable_video_url(self) -> Optional[str]:
        if self.video_source:
            if self.video_source == 'youtube':
                return f'https://videoken.com/embed/?videoID={self.video_id}&wmode=transparent&showinfo=0&rel=0&autohide=0&autoplay=1&enablejsapi=1&version=3'
            elif self.video_source == 'vimeo':
                return f'https://player.vimeo.com/video/{self.video_id}?api=1&player_id=vimeoplayer'
            elif self.video_source == 'googledrive':
                return f'https://drive.google.com/file/d/{self.video_id}/preview'
            elif self.video_source == 'raw':
                return self.video_id
        return None


def _video_property(obj) -> Optional[Dict[str, Union[str, float, datetime]]]:
    data = None
    if obj.video_source and obj.video_id:
        # Check for cached data
        data = obj._video_cache

        if not data:
            data = {
                'source': obj.video_source,
                'id': obj.video_id,
                'url': cast(str, obj.video_url),
                'embeddable_url': cast(str, obj.embeddable_video_url),
                'duration': 0.0,
                'uploaded_at': '',
                'thumbnail': '',
            }
            if obj.video_source == 'youtube':
                video_url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id={obj.video_id}&key={app.config["YOUTUBE_API_KEY"]}'
                youtube_resp = requests.get(video_url)
                if youtube_resp.status_code == 200:
                    try:
                        youtube_video = youtube_resp.json()
                        if not youtube_video or 'items' not in youtube_video:
                            raise VideoException(
                                "Unable to fetch data, please check the youtube url or API key"
                            )
                        elif not youtube_video['items']:
                            # Response has zero item for our given video ID.
                            # This will happen if the video has been removed from YouTube.
                            obj._source_video_exists = False
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
                    except JSONDecodeError as e:
                        app.logger.error(
                            "%s: Unable to parse JSON response while calling '%s'",
                            e.msg,
                            video_url,
                        )
                else:
                    app.logger.error(
                        "HTTP %s: YouTube API request failed for url '%s'",
                        youtube_resp.status_code,
                        video_url,
                    )
            elif obj.video_source == 'vimeo':
                vimeo_client = vimeo.VimeoClient(
                    token=current_app.config.get('VIMEO_ACCESS_TOKEN'),
                    key=current_app.config.get('VIMEO_CLIENT_ID'),
                    secret=current_app.config.get('VIMEO_CLIENT_SECRET'),
                )

                video_url = f'/videos/{obj.video_id}'
                vimeo_resp = vimeo_client.get(video_url)
                # vimeo_resp = requests.get(video_url)
                if vimeo_resp.status_code == 200:
                    vimeo_video = vimeo_resp.json()

                    data['duration'] = vimeo_video['duration']
                    # Vimeo returns naive datetime, we will add utc timezone to it
                    data['uploaded_at'] = utc.localize(
                        parse_isoformat(vimeo_video['release_time'])
                    )
                    data['thumbnail'] = vimeo_video['pictures']['sizes'][1]['link']
                elif vimeo_resp.status_code == 404:
                    # Video doesn't exist on Vimeo anymore
                    obj._source_video_exists = False
                else:
                    # Vimeo API down or returning unexpected values
                    obj._source_video_exists = False
                    app.logger.error(
                        "HTTP %s: Vimeo API request failed for url '%s'",
                        vimeo_resp.status_code,
                        video_url,
                    )
            obj._video_cache = data  # using _video_cache setter to set cache
    return data
