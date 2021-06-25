$(() => {
  window.Hasgeek.LabelsInit = function () {
    function applySortable() {
      $(this).sortable({
        placeholder: 'label-placeholder',
        handle: '.drag-handle',
        scroll: true,
        start: function (event, ui) {
          $('.label-placeholder').height($(ui.item).height());
        },
        update: function () {
          $(this)
            .children()
            .each(function (index) {
              let newSeq = index + 1;
              $(this).children('input[name$="seq"]').val(newSeq);
            });
        },
      });
    }
    $('#label-form').each(applySortable);

    $('.js-delete-btn').click(function (event) {
      event.preventDefault();
      let url = $(this).attr('href');
      let confirmationText = window.gettext('Are you sure you want to %s?', [
        $(this).attr('title').toLowerCase(),
      ]);

      if (window.confirm(confirmationText)) {
        $.ajax({
          type: 'POST',
          url: url,
          data: {
            csrf_token: $('meta[name="csrf-token"]').attr('content'),
          },
          success: function () {
            window.location.reload();
          },
          error(response) {
            var errorMsg = '';
            if (response.readyState === 4) {
              if (response.status === 500) {
                errorMsg = window.Hasgeek.config.errorMsg.serverError;
              } else {
                errorMsg = JSON.parse(response.responseText).error_description;
              }
            } else {
              errorMsg = window.Hasgeek.config.errorMsg.networkError;
            }
            window.toastr.error(errorMsg);
          },
        });
      }
    });
  };
});
