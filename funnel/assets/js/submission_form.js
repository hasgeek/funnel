import { Video } from './util';

$(() => {
  let waitTimer;
  const debounceInterval = 1000;

  function addEmbedVideoPlayer() {
    const videoUrl = $('.js-embed-video').data('video-src');
    Video.embedIframe($('.js-embed-video')[0], videoUrl);
  }

  function updatePreview() {
    console.log('updatePreview');
    $.ajax({
      type: 'POST',
      url: window.Hasgeek.Config.markdownPreviewApi,
      data: {
        type: 'submission',
        text: $('#body').val(),
      },
      dataType: 'json',
      timeout: window.Hasgeek.Config.ajaxTimeout,
      success(responseData) {
        $('.js-proposal-preview').html(responseData.html);
      },
    });
  }

  if ($('.js-embed-video').data('video-src') > 0) {
    addEmbedVideoPlayer();
  }

  $('body').on('click', '.js-open-modal', function (event) {
    const field = $(this).next('.js-modal-field');
    $(this).addClass('active-form-field');
    event.preventDefault();
    $('body').append('<div class="js-modal"></div>');
    $($(field).find('.js-field').detach()).insertBefore(
      $('.modal-form .js-save-modal')
    );
    $('.js-modal').append($('.modal-form').detach());
    $('.js-modal').modal();
  });

  $('body').on($.modal.AFTER_CLOSE, '.js-modal', (event) => {
    event.preventDefault();
    $('.active-form-field')
      .next('.js-modal-field')
      .append($('.modal-form').find('.js-field').detach());
    $('.js-modal-container').append($('.modal-form').detach());
    $('.js-modal').remove();
    $('.active-form-field').removeClass('active-form-field');
  });

  $('.js-close-form-modal').on('click', () => {
    $.modal.close();
  });

  $('.js-close-form-modal').on('click', () => {
    if ($('#video_url').val()) {
      $('.js-embed-video')
        .data('video-src', $('#video_url').val())
        .removeClass('mui--hide');
      $('.js-default-video-img').addClass('mui--hide');
      addEmbedVideoPlayer();
    }
  });

  const editor = document.querySelector('.CodeMirror').CodeMirror;

  editor.on('change', () => {
    console.log('change');
    if (waitTimer) clearTimeout(waitTimer);
    waitTimer = setTimeout(() => {
      updatePreview();
    }, debounceInterval);
  });
});
