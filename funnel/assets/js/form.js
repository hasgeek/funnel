import 'htmx.org';
import Form from './utils/formhelper';

window.Hasgeek.form = async ({ autosave, formId, msgElemId }) => {
  let lastSavedData = $(formId).find('[type!="hidden"]').serialize();
  let typingTimer;
  const typingWaitInterval = 1000; // wait till user stops typing for one second to send form data
  let waitingForResponse = false;
  const actionUrl = $(formId).attr('action');
  const sep = actionUrl.indexOf('?') === -1 ? '?' : '&';
  const url = `${actionUrl + sep}`;

  function haveDirtyFields() {
    const latestFormData = $(formId).find('[type!="hidden"]').serialize();
    if (latestFormData !== lastSavedData) {
      return true;
    }
    return false;
  }

  async function enableAutoSave() {
    if (!waitingForResponse && haveDirtyFields()) {
      $(msgElemId).text(window.gettext('Saving'));
      lastSavedData = $(formId).find('[type!="hidden"]').serialize();
      waitingForResponse = true;
      const form = $(formId)[0];
      const response = await fetch(`${url}form.autosave=true`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams(new FormData(form)).toString(),
      }).catch(() => {
        Form.handleFetchNetworkError();
      });
      if (response && response.ok) {
        const remoteData = await response.json();
        if (remoteData) {
          // Todo: Update window.history.pushState for new form
          $(msgElemId).text(window.gettext('Changes saved but not published'));
          if (remoteData.revision) {
            $('input[name="form.revision"]').val(remoteData.revision);
          }
          if (remoteData.form_nonce) {
            $('input[name="form_nonce"]').val(remoteData.form_nonce);
          }
          waitingForResponse = false;
        }
      } else {
        Form.formErrorHandler(formId, response);
      }
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

  if ($('textarea.markdown:not([style*="display: none"]').length) {
    const { default: codemirrorHelper } = await import('./utils/codemirror');
    $('textarea.markdown:not([style*="display: none"]').each(
      function enableCodemirror() {
        const markdownId = $(this).attr('id');
        codemirrorHelper(markdownId);
      }
    );
  }

  if ($('textarea.stylesheet:not([style*="display: none"]').length) {
    const { default: codemirrorStylesheetHelper } = await import(
      './utils/codemirror_stylesheet'
    );
    $('textarea.stylesheet:not([style*="display: none"]').each(
      function enableCodemirror() {
        const textareaId = $(this).attr('id');
        codemirrorStylesheetHelper(textareaId);
      }
    );
  }
};
