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

  $('.js-delete-btn').click(function deleteLabelButton(event) {
    event.preventDefault();
    const url = $(this).attr('href');
    const confirmationText = window.gettext('Are you sure you want to %s?', [
      $(this).attr('title').toLowerCase(),
    ]);

    if (window.confirm(confirmationText)) {
      $.ajax({
        type: 'POST',
        url,
        data: {
          csrf_token: $('meta[name="csrf-token"]').attr('content'),
        },
        success() {
          window.location.reload();
        },
        error(response) {
          const errorMsg = Form.getResponseError(response);
          window.toastr.error(errorMsg);
        },
      });
    }
  });
});
