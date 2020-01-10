import { SaveProject, Video } from './util';

$(() => {
  window.HasGeek.ProjectHeaderInit = function init(saveProjectConfig = '') {
    if (saveProjectConfig) {
      SaveProject(saveProjectConfig);
    }

    // Adding the embed video player
    if ($('.js-embed-video').length > 0) {
      $('.js-embed-video').each(function() {
        let videoUrl = $(this).data('video-src');
        Video.embedIframe(this, videoUrl);
      });
    }
  };
});
