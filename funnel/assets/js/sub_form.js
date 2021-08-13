import { Video } from './util';

$(() => {
  function addEmbedVideoPlayer() {
    const videoUrl = $('.js-embed-video').data('video-src');
    Video.embedIframe($('.js-embed-video')[0], videoUrl);
  }
  if ($('.js-embed-video').data('video-src') > 0) {
    addEmbedVideoPlayer();
  }
  $('#js-save-video').on('click', () => {
    $('.js-embed-video')
      .data('video-src', $('#video_url').val())
      .removeClass('mui--hide');
    $('.js-default-video-img').addClass('mui--hide');
    addEmbedVideoPlayer();
  });
});
