import toastr from 'toastr';
import codemirrorHelper from './utils/codemirror';
import initEmbed from './utils/initembed';
import Form from './utils/formhelper';
import { Widgets } from './utils/formwidgets';
import SortItem from './utils/sort';

$(() => {
  window.Hasgeek.submissionFormInit = function formInit(
    sortUrl,
    formId,
    markdownPreviewElem,
    markdownPreviewApi
  ) {
    function updateCollaboratorsList(responseData, updateModal = true) {
      if (updateModal) $.modal.close();
      if (responseData.message) toastr.success(responseData.message);
      if (responseData.html) $('.js-collaborator-list').html(responseData.html);
      if (updateModal) $('.js-add-collaborator').trigger('click');
    }

    async function updatePreview(view) {
      const response = await fetch(markdownPreviewApi, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          profile: 'document',
          text: view.state.doc.toString(),
        }).toString(),
      });
      if (response && response.ok) {
        const responseData = await response.json();
        if (responseData) {
          const escapeScript = responseData.html.replace('<script>', '</script>');
          $('.js-proposal-preview').html(escapeScript);
          initEmbed(markdownPreviewElem);
        }
      }
    }

    function closePreviewPanel() {
      const panel = $('.js-proposal-preview');
      const elems = $('.js-toggle-panel');
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

    $('body').on('click', '.js-open-modal', function addModal(event) {
      const field = $(this).next('.js-modal-field');
      $(this).addClass('active-form-field');
      event.preventDefault();
      $('body').append('<div class="js-modal mui-form"></div>');
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
      const modalFormId = $('.modal').find('form').attr('id');
      const url = Form.getActionUrl(modalFormId);
      const onSuccess = (responseData) => {
        updateCollaboratorsList(responseData);
      };
      const onError = (response) => {
        Form.formErrorHandler(modalFormId, response);
      };
      Form.handleFormSubmit(modalFormId, url, onSuccess, onError, {});
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
      if (
        fieldInstance.$element
          .parents('.mui-form__fields')
          .hasClass('label-select-fields')
      ) {
        fieldInstance.$element.parents('.mui-form__fields').addClass('has-error');
        $('.js-error-label').removeClass('mui--hide');
        $('.js-label-heading').addClass('mui--text-danger');
      }
    });

    $.listen('parsley:field:success', (fieldInstance) => {
      if (
        fieldInstance.$element
          .parents('.mui-form__fields')
          .hasClass('label-select-fields') &&
        fieldInstance.$element.parents('.mui-form__fields').hasClass('has-error')
      ) {
        $('.js-error-label').addClass('mui--hide');
        $('.js-label-heading').removeClass('mui--text-danger');
      }
    });

    const markdownId = $(`#${formId}`).find('textarea.markdown').attr('id');
    codemirrorHelper(markdownId, updatePreview);

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

    Widgets.handleDelete('.js-remove-collaborator', updateCollaboratorsList);

    SortItem($('.js-collaborator-list'), 'collaborator-placeholder', sortUrl);
  };
});
