import { EditorView, placeholder, keymap } from '@codemirror/view';
import { markdown, markdownLanguage, markdownKeymap } from '@codemirror/lang-markdown';
import { html } from '@codemirror/lang-html';
import { closeBrackets } from '@codemirror/autocomplete';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { defaultHighlightStyle, syntaxHighlighting } from '@codemirror/language';
import addVegaSupport from './utils/vegaembed';
import Form from './utils/formhelper';
import SortItem from './utils/sort';

$(() => {
  window.Hasgeek.submissionFormInit = function formInit(sortUrl, formId) {
    let textareaWaitTimer;
    const debounceInterval = 1000;

    function updateCollaboratorsList(responseData, updateModal = true) {
      if (updateModal) $.modal.close();
      if (responseData.message) window.toastr.success(responseData.message);
      if (responseData.html) $('.js-collaborator-list').html(responseData.html);
      if (updateModal) $('.js-add-collaborator').trigger('click');
    }

    async function updatePreview(view) {
      const response = await fetch(window.Hasgeek.Config.markdownPreviewApi, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          type: 'submission',
          text: view.state.doc.toString(),
        }).toString(),
      });
      if (response && response.ok) {
        const responseData = await response.json();
        if (responseData) {
          const escapeScript = responseData.html.replace('<script>', '</script>');
          $('.js-proposal-preview').html(escapeScript);
          addVegaSupport();
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
      window.Hasgeek.Forms.handleFormSubmit(modalFormId, url, onSuccess, onError, {});
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

    // Move this functionality to formhelper.js during to full migration to codemirror 6
    const markdownId = $(`#${formId}`).find('textarea.markdown').attr('id');
    const extensions = [
      EditorView.lineWrapping,
      placeholder('Content'),
      closeBrackets(),
      history(),
      syntaxHighlighting(defaultHighlightStyle),
      keymap.of([defaultKeymap, markdownKeymap, historyKeymap]),
      markdown({ base: markdownLanguage }),
      html(),
    ];
    const view = new EditorView({
      doc: $(`#${markdownId}`).val(),
      extensions,
      dispatch: (tr) => {
        view.update([tr]);
        $(`#${markdownId}`).val(view.state.doc.toString());
        if (textareaWaitTimer) clearTimeout(textareaWaitTimer);
        textareaWaitTimer = setTimeout(() => {
          updatePreview(view);
        }, debounceInterval);
      },
    });
    document.querySelector(`#${markdownId}`).parentNode.append(view.dom);

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

    Form.handleDelete('.js-remove-collaborator', updateCollaboratorsList);

    SortItem($('.js-collaborator-list'), 'collaborator-placeholder', sortUrl);
  };
});
