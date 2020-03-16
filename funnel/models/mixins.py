# -*- coding: utf-8 -*-

from . import db


class VideoMixin:
    video_id = db.Column(db.UnicodeText, nullable=True)
    video_source = db.Column(db.UnicodeText, nullable=True)

    @property
    def video_url(self):
        if self.video_source == 'youtube':
            return 'https://www.youtube.com/watch?v={video_id}'.format(
                video_id=self.video_id
            )
        elif self.video_source == 'vimeo':
            return 'https://vimeo.com/{video_id}'.format(video_id=self.video_id)
        else:
            return None

    @property
    def embeddable_video_url(self):
        if self.video_source == 'youtube':
            return '//www.youtube.com/embed/{video_id}?wmode=transparent&showinfo=0&rel=0&autohide=0&autoplay=0&enablejsapi=1&version=3'.format(
                video_id=self.video_id
            )
        elif self.video_source == 'vimeo':
            return '//player.vimeo.com/video/{video_id}?api=1&player_id=vimeoplayer'.format(
                video_id=self.video_id
            )
        else:
            return None
