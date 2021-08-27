$(() => {
  window.Hasgeek.AutoSaveInit = function (config) {
    let typingTimer;
    let typingWaitInterval = 1000; // wait till user stops typing for one second to send form data
    let waitingForResponse = false;
    let lastSavedData = '';
    let formElem = $(`#${config.refId}`);
    let saveAlertElem = $(config.msgId);

    function haveDirtyFields() {
      let latestFormData = formElem.find('[type!="hidden"]').serialize();
      if (latestFormData !== lastSavedData) {
        return true;
      }
      return false;
    }

    function autosaveForm() {
      let actionUrl = formElem.attr('action');
      let sep = actionUrl.indexOf('?') === -1 ? '?' : '&';
      if (!waitingForResponse && haveDirtyFields()) {
        $.ajax({
          type: 'POST',
          url: actionUrl + sep + 'form.autosave=true',
          data: formElem.serialize(),
          dataType: 'json',
          timeout: 15000,
          beforeSend: function () {
            saveAlertElem.text('Autosaving…');
            lastSavedData = formElem.find('[type!="hidden"]').serialize();
            waitingForResponse = true;
          },
          success: function (remoteData) {
            // Todo: Update window.history.pushState for new form
            saveAlertElem.text(
              window.gettext('Changes saved but not published')
            );
            if (remoteData.revision) {
              $('input[name="form.revision"]').val(remoteData.revision);
            }
            if (remoteData.form_nonce) {
              $('input[name="form_nonce"]').val(remoteData.form_nonce);
            }
            waitingForResponse = false;
            autosaveForm();
          },
          error: function (response) {
            var errorMsg = '';
            waitingForResponse = false;
            if (response.readyState === 4) {
              if (response.status === 500) {
                errorMsg = window.Hasgeek.Config.errorMsg.serverError;
              } else {
                // There is a version mismatch, notify user to reload the page.
                waitingForResponse = true;
                errorMsg = JSON.parse(response.responseText).error_description;
              }
            } else {
              errorMsg = window.Hasgeek.Config.errorMsg.networkError;
            }
            saveAlertElem.text(errorMsg);
            window.toastr.error(errorMsg);
          },
        });
        return;
      }

      $('input[name="form.revision"]').val()
        ? saveAlertElem.text(
            window.gettext('These changes have not been published yet')
          )
        : '';

      formElem.on('change', function () {
        autosaveForm();
      });

      formElem.on('keyup', function () {
        if (typingTimer) clearTimeout(typingTimer);
        typingTimer = setTimeout(autosaveForm, typingWaitInterval);
      });

      $(window).bind('beforeunload', function () {
        if (haveDirtyFields()) {
          return window.gettext(
            'You have unsaved changes on this page. Do you want to leave this page?'
          );
        }
        return false;
      });
    }
  };
});
