import 'htmx.org';
import Form from './utils/formhelper';
import codemirrorHelper from './utils/codemirror';

window.Hasgeek.form = ({ autosave, formId, msgElemId }) => {
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

  $('textarea.markdown:not([style*="display: none"]').each(function enableCodemirror() {
    const markdownId = $(this).attr('id');
    codemirrorHelper(markdownId);
  });

  Form.activate_select2();

  window.Hasgeek.MapMarker = function (field) {
    this.field = field;
    this.activate();
    return this;
  };

  window.Hasgeek.MapMarker.prototype.activate = function () {
    const self = this;
    window.Hasgeek.Forms.preventSubmitOnEnter(this.field.location_id);

    // locationpicker.jquery.js
    $(`#${this.field.map_id}`).locationpicker({
      location: self.getDefaultLocation(),
      radius: 0,
      zoom: 18,
      inputBinding: {
        latitudeInput: $(`#${this.field.latitude_id}`),
        longitudeInput: $(`#${this.field.longitude_id}`),
        locationNameInput: $(`#${this.field.location_id}`),
      },
      enableAutocomplete: true,
      onchanged() {
        if ($(`#${self.field.location_id}`).val()) {
          $(`#${self.field.map_id}`).removeClass('mui--hide');
        }
      },
      onlocationnotfound() {},
      oninitialized() {
        // Locationpicker sets latitude and longitude field value to 0,
        // this is to empty the fields and hide the map
        if (!$(`#${self.field.location_id}`).val()) {
          $(`#${self.field.latitude_id}`).val('');
          $(`#${self.field.longitude_id}`).val('');
          $(`#${self.field.map_id}`).addClass('mui--hide');
        }
      },
    });

    // On clicking clear, empty latitude, longitude, location fields and hide map
    $(`#${this.field.clear_id}`).on('click', (event) => {
      event.preventDefault();
      $(`#${self.field.latitude_id}`).val('');
      $(`#${self.field.longitude_id}`).val('');
      $(`#${self.field.location_id}`).val('');
      $(`#${self.field.map_id}`).addClass('mui--hide');
    });
  };

  window.Hasgeek.MapMarker.prototype.getDefaultLocation = function () {
    let latitude;
    let longitude;
    latitude = $(`#${this.field.latitude_id}`).val();
    longitude = $(`#${this.field.longitude_id}`).val();
    return { latitude, longitude };
  };
};
