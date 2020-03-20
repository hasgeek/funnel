# -*- coding: utf-8 -*-


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
    def thumbnail_url(self):
        if self.video_source:
            if self.video_source == 'youtube':
                return '//i.ytimg.com/vi/{video_id}/mqdefault.jpg'.format(
                    video_id=self.video_id
                )
            elif self.video_source == 'vimeo':
                return '//i.vimeocdn.com/video/{video_id}_200x150.jpg'.format(
                    video_id=self.video_id
                )
        return None
