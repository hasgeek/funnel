from __future__ import annotations

from datetime import datetime
from typing import Optional, Union, cast

from flask import current_app

from pytz import utc
from sentry_sdk import capture_exception
from typing_extensions import TypedDict
import requests
import simplejson
import vimeo

from coaster.utils import parse_duration, parse_isoformat

from .. import redis_store
from ..models import Proposal, Session, VideoError, VideoMixin


class YoutubeApiError(VideoError):
    """The YouTube API failed."""


class VideoData(TypedDict):
    """Dictionary for video data, as used in templates."""

    source: str
    id: str
    url: str
    embeddable_url: str
    duration: float
    uploaded_at: Union[str, datetime]
    thumbnail: str


def video_cache_key(obj: VideoMixin) -> str:
    if obj.video_source and obj.video_id:
        return 'video_cache/' + obj.video_source + '/' + obj.video_id
    raise VideoError("No video source or ID to create a cache key")


def get_video_cache(obj: VideoMixin) -> Optional[VideoData]:
    data = redis_store.hgetall(video_cache_key(obj))
    if data:
        if 'uploaded_at' in data and data['uploaded_at']:
            data['uploaded_at'] = parse_isoformat(data['uploaded_at'], naive=False)
        if 'duration' in data and data['duration']:
            data['duration'] = float(data['duration'])
    return data


def set_video_cache(obj: VideoMixin, data: VideoData, exists: bool = True) -> None:
    cache_key = video_cache_key(obj)

    copied_data = data.copy()
    if copied_data['uploaded_at']:
        copied_data['uploaded_at'] = cast(
            datetime, copied_data['uploaded_at']
        ).isoformat()
    redis_store.hmset(cache_key, copied_data)

    # if video exists at source, cache for 2 days, if not, for 6 hours
    hours_to_cache = 2 * 24 if exists else 6
    redis_store.expire(cache_key, 60 * 60 * hours_to_cache)


@Proposal.views('video', cached_property=True)
@Session.views('video', cached_property=True)
def video_property(obj: VideoMixin) -> Optional[VideoData]:
    data: Optional[VideoData] = None
    exists = True
    if obj.video_source and obj.video_id:
        # Check for cached data
        data = get_video_cache(obj)

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
                video_url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id={obj.video_id}&key={current_app.config["YOUTUBE_API_KEY"]}'
                try:
                    youtube_resp = requests.get(video_url, timeout=30)
                except requests.exceptions.RequestException as exc:
                    current_app.logger.error("YouTube API request error: %s", repr(exc))
                    capture_exception(exc)
                    return data
                if youtube_resp.status_code == 200:
                    try:
                        youtube_video = youtube_resp.json()
                        if not youtube_video or 'items' not in youtube_video:
                            raise YoutubeApiError(
                                "Unable to fetch data, please check the youtube url or API key"
                            )
                        elif not youtube_video['items']:
                            # Response has zero item for our given video ID.
                            # This will happen if the video has been removed from YouTube.
                            exists = False
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
                    except simplejson.JSONDecodeError as exc:
                        current_app.logger.error(
                            "%s: Unable to parse JSON response while calling '%s'",
                            exc.msg,
                            video_url,
                        )
                        capture_exception(exc)
                else:
                    current_app.logger.error(
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
                # vimeo_resp = requests.get(video_url, timeout=30)
                if vimeo_resp.status_code == 200:
                    vimeo_video = vimeo_resp.json()

                    data['duration'] = float(vimeo_video['duration'])
                    # Vimeo returns naive datetime, we will add utc timezone to it
                    data['uploaded_at'] = utc.localize(
                        parse_isoformat(vimeo_video['release_time'])
                    )
                    data['thumbnail'] = vimeo_video['pictures']['sizes'][1]['link']
                elif vimeo_resp.status_code == 404:
                    # Video doesn't exist on Vimeo anymore
                    exists = False
                else:
                    # Vimeo API down or returning unexpected values
                    exists = False
                    current_app.logger.error(
                        "HTTP %s: Vimeo API request failed for url '%s'",
                        vimeo_resp.status_code,
                        video_url,
                    )
            set_video_cache(obj, data, exists)
    return data
