from datetime import datetime
from typing import Dict, Optional, Union, cast

from flask import current_app

from pytz import utc
from simplejson import JSONDecodeError
import requests
import vimeo

from coaster.utils import parse_duration, parse_isoformat

from ..models import Proposal, Session


class YoutubeApiException(Exception):
    pass


@Proposal.views('video', cached_property=True)
@Session.views('video', cached_property=True)
def video_property(obj) -> Optional[Dict[str, Union[str, float, datetime]]]:
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
                video_url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id={obj.video_id}&key={current_app.config["YOUTUBE_API_KEY"]}'
                youtube_resp = requests.get(video_url)
                if youtube_resp.status_code == 200:
                    try:
                        youtube_video = youtube_resp.json()
                        if not youtube_video or 'items' not in youtube_video:
                            raise YoutubeApiException(
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
                        current_app.logger.error(
                            "%s: Unable to parse JSON response while calling '%s'",
                            e.msg,
                            video_url,
                        )
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
                    current_app.logger.error(
                        "HTTP %s: Vimeo API request failed for url '%s'",
                        vimeo_resp.status_code,
                        video_url,
                    )
            obj._video_cache = data  # using _video_cache setter to set cache
    return data
