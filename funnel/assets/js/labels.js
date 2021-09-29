import Form from './utils/formhelper';

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

  const msg = 'Are you sure you want to %s?';
  const onSuccessFn = () => {
    window.location.reload();
  };
  Form.handleDelete('.js-delete-btn', msg, onSuccessFn);
});
