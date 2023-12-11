import toastr from 'toastr';
import Form from './formhelper';

export const Widgets = {
  activateToggleSwitch(checkboxId, callbckfn = '') {
    function postForm() {
      let submitting = false;
      return (checkboxElem) => {
        if (!submitting) {
          submitting = true;
          const checkbox = $(checkboxElem);
          const currentState = checkboxElem.checked;
          const previousState = !currentState;
          const formData = new FormData(checkbox.parent('form')[0]);
          if (!currentState) {
            formData.append(checkbox.attr('name'), false);
          }

          fetch(checkbox.parent('form').attr('action'), {
            method: 'POST',
            headers: {
              Accept: 'application/json',
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams(formData).toString(),
          })
            .then((response) => response.json())
            .then((responseData) => {
              if (responseData && responseData.message) {
                toastr.success(responseData.message);
              }
              if (callbckfn) {
                callbckfn();
              }
              submitting = false;
            })
            .catch((error) => {
              const errorMsg = Form.handleAjaxError(error);
              toastr.error(errorMsg);
              checkbox.prop('checked', previousState);
              submitting = false;
            });
        }
      };
    }

    const throttleSubmit = postForm();

    $('body').on('change', checkboxId, function submitToggleSwitch() {
      throttleSubmit(this);
    });

    $('body').on(
      'click',
      '.js-dropdown-toggle',
      function stopPropagation(event) {
        event.stopPropagation();
      }
    );
  },
  openSubmissionToggle(checkboxId, cfpStatusDiv) {
    const onSuccess = () => {
      $(cfpStatusDiv).toggleClass('mui--hide');
    };
    this.activateToggleSwitch(checkboxId, onSuccess);
  },
  handleDelete(elementClass, onSucessFn) {
    $('body').on('click', elementClass, async function remove(event) {
      event.preventDefault();
      const url = $(this).attr('data-href');
      const confirmationText = window.gettext(
        'Are you sure you want to remove %s?',
        [$(this).attr('title')]
      );

      /* eslint-disable no-alert */
      if (window.confirm(confirmationText)) {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            csrf_token: $('meta[name="csrf-token"]').attr('content'),
          }).toString(),
        }).catch(() => {
          toastr.error(window.Hasgeek.Config.errorMsg.networkError);
        });
        if (response && response.ok) {
          const responseData = await response.json();
          if (responseData) {
            onSucessFn(responseData);
          }
        } else {
          Form.handleAjaxError(response);
        }
      }
    });
  },
};

export async function activateFormWidgets() {
  $('.js-show-password').on('click', function showPassword(event) {
    event.preventDefault();
    $(this).parent().find('.js-password-toggle').toggleClass('mui--hide');
    $(this).parent().find('input').attr('type', 'text');
  });
  $('.js-hide-password').on('click', function hidePassword(event) {
    event.preventDefault();
    $(this).parent().find('.js-password-toggle').toggleClass('mui--hide');
    $(this).parent().find('input').attr('type', 'password');
  });

  // Toggle between OTP/Password login
  $('.js-toggle-login').on('click', function toggleOTPField(event) {
    event.preventDefault();
    if ($(this).attr('id') === 'use-otp-login') {
      $('.js-password-field').find('input').val('');
    }
    $('.js-fields-toggle').toggleClass('mui--hide');
  });

  $('.js-password-field input').on('change', function togglePasswordField() {
    if ($('.js-password-field').hasClass('mui--hide')) {
      $('.js-fields-toggle').toggleClass('mui--hide');
    }
  });

  // Change username field input mode to tel in login form
  if ($('#loginformwrapper').length && $('#username').length) {
    $('#username').attr('inputmode', 'tel');
    $('#username').attr('autocomplete', 'tel');
    $('.js-keyboard-switcher[data-inputmode="tel"]').addClass('active');
  }

  // Add support to toggle username field input mode between tel & email to change keyboard in mobile
  $('.js-keyboard-switcher').on(
    'click touchstart touchend',
    function keyboardSwitcher(event) {
      event.preventDefault();
      const inputMode = $(this).data('inputmode');
      $('.js-keyboard-switcher').removeClass('active');
      $(this).addClass('active');
      $('#username').attr('inputmode', inputMode);
      $('#username').attr('autocomplete', inputMode);
      $('#username').blur();
      $('#username').focus();
    }
  );

  if (
    $(
      'textarea.markdown:not([style*="display: none"], .activating, .activated, .no-codemirror)'
    ).length
  ) {
    const { default: codemirrorHelper } = await import('./codemirror');
    $(
      'textarea.markdown:not([style*="display: none"]:not(.activating):not(.activated)'
    ).each(function enableCodemirror() {
      const markdownId = $(this).attr('id');
      $(`#${markdownId}`).addClass('activating');
      codemirrorHelper(markdownId);
    });
  }

  if (
    $(
      'textarea.stylesheet:not([style*="display: none"]:not(.activating):not(.activated)'
    ).length
  ) {
    const { default: codemirrorStylesheetHelper } = await import(
      './codemirror_stylesheet'
    );
    $(
      'textarea.stylesheet:not([style*="display: none"]:not(.activating):not(.activated)'
    ).each(function enableCodemirrorForStylesheet() {
      const textareaId = $(this).attr('id');
      $(`#${textareaId}`).addClass('activating');
      codemirrorStylesheetHelper(textareaId);
    });
  }
}

export class MapMarker {
  constructor(field) {
    this.field = field;
    this.activate();
  }

  activate() {
    const self = this;
    Form.preventSubmitOnEnter(this.field.locationId);

    // locationpicker.jquery.js
    $(`#${this.field.mapId}`).locationpicker({
      location: self.getDefaultLocation(),
      radius: 0,
      zoom: 18,
      inputBinding: {
        latitudeInput: $(`#${this.field.latitudeId}`),
        longitudeInput: $(`#${this.field.longitudeId}`),
        locationNameInput: $(`#${this.field.locationId}`),
      },
      enableAutocomplete: true,
      onchanged() {
        if ($(`#${self.field.locationId}`).val()) {
          $(`#${self.field.mapId}`).removeClass('mui--hide');
        }
      },
      onlocationnotfound() {},
      oninitialized() {
        // Locationpicker sets latitude and longitude field value to 0,
        // this is to empty the fields and hide the map
        if (!$(`#${self.field.locationId}`).val()) {
          $(`#${self.field.latitudeId}`).val('');
          $(`#${self.field.longitudeId}`).val('');
          $(`#${self.field.mapId}`).addClass('mui--hide');
        }
      },
    });

    // On clicking clear, empty latitude, longitude, location fields and hide map
    $(`#${this.field.clearId}`).on('click', (event) => {
      event.preventDefault();
      $(`#${self.field.latitudeId}`).val('');
      $(`#${self.field.longitudeId}`).val('');
      $(`#${self.field.locationId}`).val('');
      $(`#${self.field.mapId}`).addClass('mui--hide');
    });
  }

  getDefaultLocation() {
    const latitude = $(`#${this.field.latitudeId}`).val();
    const longitude = $(`#${this.field.longitudeId}`).val();
    return { latitude, longitude };
  }
}
