import { SaveProject, Video } from './util';

$(() => {
  window.Hasgeek.ProjectHeaderInit = function init(saveProjectConfig = '') {
    if (saveProjectConfig) {
      SaveProject(saveProjectConfig);
    }

    // Adding the embed video player
    if ($('.js-embed-video').length > 0) {
      $('.js-embed-video').each(function () {
        let videoUrl = $(this).data('video-src');
        Video.embedIframe(this, videoUrl);
      });
    }

    $('a#register-btn').click(function () {
      $(this).modal();
    });

    if (window.location.hash === '#register-modal') {
      $('a#register-btn').modal();
    }
  };
});
