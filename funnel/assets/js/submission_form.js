import addVegaSupport from './utils/vegaembed';
import Form from './utils/formhelper';

$(() => {
  let textareaWaitTimer;
  const debounceInterval = 1000;

  function updateCollaboratorsList(responseData, updateModal = true) {
    if (updateModal) $.modal.close();
    if (responseData.message) window.toastr.success(responseData.message);
    if (responseData.html) $('.js-collaborator-list').html(responseData.html);
    if (updateModal) $('.js-add-collaborator').trigger('click');
  }

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
        addVegaSupport();
      },
    });
  }

  function closePreviewPanel() {
    const panel = $('.js-proposal-preview');
    const elems = $('.js-switch-panel');
    if (panel.hasClass('close')) {
      panel.animate({ top: '52' });
    } else {
      panel.animate({ top: '100vh' });
    }
    panel.toggleClass('close');
    elems.toggleClass('mui--hide');
  }

  function removeLineBreaks(text) {
    return text.replace(/(\r\n|\n|\r)/gm, ' ').replace(/\s+/g, ' ');
  }

  $('body').on('click', '.js-open-modal', function (event) {
    const field = $(this).next('.js-modal-field');
    $(this).addClass('active-form-field');
    event.preventDefault();
    $('body').append('<div class="js-modal"></div>');
    $('.modal-form').append($(field).find('.js-field').detach());
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

  $('body').on($.modal.OPEN, '.modal', (event) => {
    event.preventDefault();
    $('select.select2').select2('open').trigger('select2:open');
    const formId = $('.modal').find('form').attr('id');
    const url = Form.getActionUrl(formId);
    const onSuccess = (responseData) => {
      updateCollaboratorsList(responseData);
    };
    const onError = (response) => {
      Form.formErrorHandler(formId, response);
    };
    window.Hasgeek.Forms.handleFormSubmit(formId, url, onSuccess, onError, {});
  });

  $('.js-switch-panel').on('click', (event) => {
    event.preventDefault();
    closePreviewPanel();
  });

  $('button[name="submit"]').on('click', () => {
    if (!$('.js-proposal-preview').hasClass('close')) {
      closePreviewPanel();
    }
  });

  $.listen('parsley:field:error', (fieldInstance) => {
    if (fieldInstance.$element.data('parsley-multiple'))
      $('.label-error-icon').removeClass('mui--hide');
  });

  const editor = document.querySelector('.CodeMirror').CodeMirror;

  editor.on('change', () => {
    if (textareaWaitTimer) clearTimeout(textareaWaitTimer);
    textareaWaitTimer = setTimeout(() => {
      updatePreview();
    }, debounceInterval);
  });

  $('#title')
    .keypress((event) => {
      if (event.which === 13) return false;
      return true;
    })
    .blur((event) => {
      return $(event.currentTarget).val(
        removeLineBreaks($(event.currentTarget).val())
      );
    });

  const onSuccessFn = (responseData) => {
    updateCollaboratorsList(responseData, false);
  };
  Form.handleDelete('.js-remove-collaborator', onSuccessFn);
});
