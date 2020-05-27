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

    $('a#register-btn').click(function() {
      $(this).modal();
    });

    $('#register-modal').on($.modal.CLOSE, () => {
      window.history.replaceState(
        '',
        '',
        window.location.pathname + window.location.search
      );
    });

    if (window.location.hash === '#register-modal') {
      $('a#register-btn').modal();
    }

    window.addEventListener(
      'hashchange',
      function() {
        if (window.location.hash == '') {
          $.modal.close();
        }
      },
      false
    );
  };
});
