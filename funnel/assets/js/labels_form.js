import 'jquery-ui';
import 'jquery-ui-sortable-npm';
import 'jquery-ui-touch-punch';
import 'emojionearea';
import toastr from 'toastr';
import { activateFormWidgets } from './utils/formWidgets';

$(() => {
  window.Hasgeek.LabelsFormInit = function LabelsFormInit(formHtml) {
    function initEmojiPicker() {
      $('input.field-icon_emoji:not([style*="display: none"])').emojioneArea({
        pickerPosition: 'bottom',
        autocomplete: false,
        standalone: true,
      });
    }
    function applySortable() {
      $(this).sortable({
        placeholder: $(this).data('drag-placeholder'),
        cursor: 'move',
        update() {
          $(this)
            .children()
            .each(function updateSeq(index) {
              $(this)
                .children('input[name$="seq"]')
                .val(index + 1);
            });
        },
      });
    }
    $('#add-sublabel-form').click((e) => {
      e.preventDefault();
      $('#child-form').append(formHtml);
      activateFormWidgets();
      initEmojiPicker();
      $('.js-required-field').removeClass('mui--hide');
      $('.js-required-field input').prop('checked', true);
      $('#child-form').each(applySortable);
    });
    $('#child-form').on('click', '.js-remove-sublabel-form', function removeSubForm(e) {
      e.preventDefault();
      $(this).parent().remove();
    });
    initEmojiPicker();
    $('#child-form').each(applySortable);

    $('#label-form').on('submit', (e) => {
      const optionCount = $('#child-form').find('.ui-draggable-box').length;
      if (optionCount === 1) {
        e.preventDefault();
        toastr.error('Minimum 2 or more options are needed');
        return false;
      }
      return true;
    });
  };
});
