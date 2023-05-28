"""Mixin class for models that support a single embedded video."""

from __future__ import annotations

from typing import Optional, Tuple

from furl import furl

from . import declarative_mixin, sa

__all__ = ['VideoMixin', 'VideoError', 'parse_video_url']


class VideoError(Exception):
    """A video could not be processed (base exception)."""


def parse_video_url(video_url: str) -> Tuple[str, str]:
    video_source = 'raw'
    video_id: Optional[str] = video_url

    parsed = furl(video_url)
    if not parsed.host:
        raise ValueError("The video URL must be an absolute URL")

    if parsed.host in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        video_source = 'youtube'
        video_id = None
        if parsed.path == '/watch':
            video_id = parsed.query.params.get('v')
        elif len(parsed.path.segments) == 2 and parsed.path.segments[0] in (
            'embed',
            'live',
        ):
            video_id = parsed.path.segments[1]
        if not video_id:
            raise ValueError("Unparseable YouTube URL")

    elif parsed.host == 'youtu.be':
        video_source = 'youtube'
        video_id = parsed.path.segments[0]
        if not video_id:
            raise ValueError("Unparseable YouTube URL")
    elif parsed.host in ['vimeo.com', 'www.vimeo.com']:
        video_source = 'vimeo'
        video_id = parsed.path.segments[0]
        if not video_id:
            raise ValueError("Unparseable Vimeo URL")
    elif parsed.host == 'drive.google.com':
        video_source = 'googledrive'
        video_id = None
        if parsed.path.segments[0] == 'open':
            video_id = parsed.query.params.get('id')
        elif len(parsed.path.segments) > 2 and parsed.path.segments[:2] == [
            'file',
            'd',
        ]:
            video_id = parsed.path.segments[2]
        if not video_id:
            raise ValueError("Unsupported Google Drive URL")

    return video_source, video_id


def make_video_url(video_source: str, video_id: str) -> str:
    if video_source == 'youtube':
        return f'https://www.youtube.com/watch?v={video_id}'
    if video_source == 'vimeo':
        return f'https://vimeo.com/{video_id}'
    if video_source == 'googledrive':
        return f'https://drive.google.com/file/d/{video_id}/view'
    if video_source == 'raw':
        return video_id
    raise ValueError("Unknown video source")


@declarative_mixin
class VideoMixin:
    video_id = sa.orm.mapped_column(sa.UnicodeText, nullable=True)
    video_source = sa.orm.mapped_column(sa.UnicodeText, nullable=True)

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
                return (
                    f'https://videoken.com/embed/?videoID={self.video_id}'
                    f'&wmode=transparent&showinfo=0&rel=0&autohide=0&autoplay=1'
                    f'&enablejsapi=1&version=3'
                )
            if self.video_source == 'vimeo':
                return (
                    f'https://player.vimeo.com/video/{self.video_id}'
                    f'?api=1&player_id=vimeoplayer'
                )
            if self.video_source == 'googledrive':
                return f'https://drive.google.com/file/d/{self.video_id}/preview'
            if self.video_source == 'raw':
                return self.video_id
        return None
