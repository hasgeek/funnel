# -*- coding: utf-8 -*-


from . import db


class VideoMixin:
    video_id = db.Column(db.UnicodeText, nullable=True)
    video_source = db.Column(db.UnicodeText, nullable=True)

    @property
    def video(self):
        data = None
        if self.video_source is not None:
            data = {'source': self.video_source, 'id': self.video_id}
            if data['source'] == 'youtube':
                data[
                    'url'
                ] = '//www.youtube.com/embed/{video_id}?wmode=transparent&showinfo=0&rel=0&autohide=0&autoplay=0&enablejsapi=1&version=3'.format(
                    video_id=self.video_id
                )
            elif data['source'] == 'vimeo':
                data[
                    'url'
                ] = '//player.vimeo.com/video/{video_id}?api=1&player_id=vimeoplayer'.format(
                    video_id=self.video_id
                )
            else:
                data['url'] = self.video_id
        return data
