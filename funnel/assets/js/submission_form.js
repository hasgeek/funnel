$(() => {
  let waitTimer;
  const debounceInterval = 1000;

  function updatePreview() {
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
    const videoUrl = $('#video_url').val();
    if (videoUrl) {
      $('.js-embed-video').text(videoUrl);
    }
  });

  const editor = document.querySelector('.CodeMirror').CodeMirror;

  editor.on('change', () => {
    if (waitTimer) clearTimeout(waitTimer);
    waitTimer = setTimeout(() => {
      updatePreview();
    }, debounceInterval);
  });

  $('.js-switch-panel').on('click', (event) => {
    event.preventDefault();
    const panel = $('.js-proposal-preview');
    const elems = $('.js-switch-panel');
    if (panel.hasClass('close')) {
      panel.animate({ top: '52' });
    } else {
      panel.animate({ top: '100vh' });
    }
    panel.toggleClass('close');
    elems.toggleClass('mui--hide');
  });

  /* Adding video preview
  function addEmbedVideoPlayer() {
    const videoUrl = $('.js-embed-video').data('video-src');
    Video.embedIframe($('.js-embed-video')[0], videoUrl);
  }

  if ($('.js-embed-video').data('video-src') > 0) {
    addEmbedVideoPlayer();
  }

  $('.js-close-form-modal').on('click', () => {
    if ($('#video_url').val()) {
      $('.js-embed-video')
        .data('video-src', $('#video_url').val())
        .removeClass('mui--hide');
      $('.js-default-video-img').addClass('mui--hide');
      addEmbedVideoPlayer();
    }
  });
  */
});
