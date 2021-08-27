from __future__ import annotations

from typing import Optional, Tuple
import urllib.parse

from baseframe import _

from . import db

__all__ = ['VideoMixin', 'VideoError', 'parse_video_url']


class VideoError(Exception):
    """A video could not be processed (base exception)."""


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
                    _("This must be a shareable URL for a single file in Google Drive")
                )
        elif parsed.path.startswith('/file/d/'):
            video_id = parsed.path.lstrip('/file/d/').rstrip('/view').rstrip('/preview')
            video_source = 'googledrive'
        else:
            raise ValueError(
                _("This must be a shareable URL for a single file in Google Drive")
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

    @property
    def video_url(self) -> Optional[str]:
        if self.video_source and self.video_id:
            return make_video_url(self.video_source, self.video_id)
        return None

    @video_url.setter
    def video_url(self, value: str):
        if not value:
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
