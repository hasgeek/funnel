window.Hasgeek.form = ({ autosave, formId, msgElemId }) => {
  let lastSavedData = $(formId).find('[type!="hidden"]').serialize();
  let typingTimer;
  const typingWaitInterval = 1000; // wait till user stops typing for one second to send form data
  let waitingForResponse = false;
  const actionUrl = $(formId).attr('action');
  const sep = actionUrl.indexOf('?') === -1 ? '?' : '&';
  const url = `${actionUrl + sep}`;

  function haveDirtyFields() {
    const latestFormData = $('form').find('[type!="hidden"]').serialize();
    if (latestFormData !== lastSavedData) {
      return true;
    }
    return false;
  }

  function enableAutoSave() {
    if (!waitingForResponse && haveDirtyFields()) {
      $.ajax({
        type: 'POST',
        url: `${url}form.autosave=true`,
        data: $(formId).serialize(),
        dataType: 'json',
        timeout: 15000,
        beforeSend() {
          $(msgElemId).text(window.gettext('Saving'));
          lastSavedData = $(formId).find('[type!="hidden"]').serialize();
          waitingForResponse = true;
        },
        success(remoteData) {
          // Todo: Update window.history.pushState for new form
          $(msgElemId).text(window.gettext('Changes saved but not published'));
          if (remoteData.revision) {
            $('input[name="form.revision"]').val(remoteData.revision);
          }
          if (remoteData.form_nonce) {
            $('input[name="form_nonce"]').val(remoteData.form_nonce);
          }
          waitingForResponse = false;
        },
        error(response) {
          let errorMsg = '';
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
          $(msgElemId).text(errorMsg);
          window.toastr.error(errorMsg);
        },
      });
    }
  }

  $(window).bind('beforeunload', () => {
    if (haveDirtyFields()) {
      return window.gettext(
        'You have unsaved changes on this page. Do you want to leave this page?'
      );
    }
    return true;
  });

  $(formId).on('submit', () => {
    $(window).off('beforeunload');
  });

  if (autosave) {
    if ($('input[name="form.revision"]').val()) {
      $(msgElemId).text(window.gettext('These changes have not been published yet'));
    }

    $(formId).on('change', () => {
      enableAutoSave();
    });

    $(formId).on('keyup', () => {
      if (typingTimer) clearTimeout(typingTimer);
      typingTimer = setTimeout(enableAutoSave, typingWaitInterval);
    });
  }
};
