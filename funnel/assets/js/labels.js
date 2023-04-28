import 'jquery-ui';
import 'jquery-ui-sortable-npm';
import 'jquery-ui-touch-punch';
import { Widgets } from './utils/form_widgets';

$(() => {
  function applySortable() {
    $(this).sortable({
      placeholder: 'label-placeholder',
      handle: '.drag-handle',
      scroll: true,
      start(event, ui) {
        $('.label-placeholder').height($(ui.item).height());
      },
      update() {
        $(this)
          .children()
          .each(function setNewSeq(index) {
            const newSeq = index + 1;
            $(this).children('input[name$="seq"]').val(newSeq);
          });
      },
    });
  }
  $('#label-form').each(applySortable);

  const onSuccessFn = () => {
    window.location.reload();
  };
  Widgets.handleDelete('.js-delete-btn', onSuccessFn);
});
