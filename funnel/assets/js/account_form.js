import 'htmx.org';
import Form from './utils/formhelper';

window.Hasgeek.Accountform = ({
  formId,
  usernameField,
  passwordField,
  passwordForm,
  accountUsernameUrl,
  passwordCheckUrl,
}) => {
  $(formId)
    .parsley()
    .subscribe('parsley:field:validated', () => {
      if ($(formId).parsley().isValid())
        $(formId).addClass('parsley-valid').removeClass('parsley-invalid');
      else $(formId).addClass('parsley-invalid').removeClass('parsley-valid');
    });

  let typingTimer;
  let typingTimerUsername;
  const typingWaitInterval = 100;
  let waitingForResponse = false;
  let waitingForUsernameResponse = false;

  async function checkUsernameAvailability(field) {
    if (!waitingForUsernameResponse && $(field).val()) {
      waitingForUsernameResponse = true;
      const response = await fetch(accountUsernameUrl, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: $(field).val(),
          csrf_token: $('meta[name="csrf-token"]').attr('content'),
        }),
      }).catch(() => {
        window.toastr.error(window.Hasgeek.Config.errorMsg.networkError);
      });
      if (response && response.ok) {
        const remoteData = await response.json();
        if (remoteData) {
          waitingForUsernameResponse = false;
          const fieldWrapper = $(field).closest('.mui-form__controls');
          if (remoteData.status === 'error') {
            $(field).closest('.mui-form__fields').addClass('has-error');
            if ($(fieldWrapper).find('p.mui-form__error').length) {
              $(fieldWrapper)
                .find('p.mui-form__error')
                .text(remoteData.error_description);
            } else {
              const errorTxt = $('<p class="mui-form__error"></p>').text(
                remoteData.error_description
              );
              $(errorTxt).insertBefore($(fieldWrapper).find('.mui-form__helptext'));
            }
          } else {
            $(field).closest('.mui-form__fields').removeClass('has-error');
            $(fieldWrapper).find('p.mui-form__error').remove();
          }
        }
      } else {
        waitingForUsernameResponse = false;
        Form.getFetchError(response);
      }
    }
  }

  async function checkPasswordStrength(field) {
    if (!waitingForResponse && $(field).val()) {
      waitingForResponse = true;
      const response = await fetch(passwordCheckUrl, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          password: $(field).val(),
          csrf_token: $('meta[name="csrf-token"]').attr('content'),
        }),
      }).catch(() => {
        window.toastr.error(window.Hasgeek.Config.errorMsg.networkError);
      });
      if (response && response.ok) {
        const remoteData = await response.json();
        waitingForResponse = false;
        if (remoteData.status === 'ok') {
          $(field).parent().find('.progress').addClass('progress--show');
          const widthPercentage = `${remoteData.result.strength * 100}%`;
          $(field).parent().find('.progress__bar').css('width', widthPercentage);
          $(field)
            .parent()
            .find('.progress__txt')
            .text(remoteData.result.strength_verbose);
          if (remoteData.result.is_weak) {
            $(field)
              .parent()
              .find('.progress__bar')
              .removeClass('progress__bar--success')
              .addClass('progress__bar--danger');
            $(passwordForm).removeClass('password-valid');
            $(field)
              .parent()
              .find('.password-strength-icon')
              .removeClass('password-strength-icon--show');
            $(field)
              .parent()
              .find('.js-password-weak')
              .addClass('password-strength-icon--show');
          } else {
            $(passwordForm).addClass('password-valid');
            $(field)
              .parent()
              .find('.password-strength-icon')
              .removeClass('password-strength-icon--show');
            $(field)
              .parent()
              .find('.js-password-good')
              .addClass('password-strength-icon--show');
            $(field)
              .parent()
              .find('.progress__bar')
              .removeClass('progress__bar--danger')
              .addClass('progress__bar--success');
          }
        } else {
          waitingForResponse = false;
          Form.getFetchError(response);
        }
      }
    } else if (!$(field).val()) {
      $(field).parent().find('.progress').removeClass('progress--show');
    }
  }

  if (usernameField) {
    $(usernameField).on('change', function handleUsernameFieldChange() {
      checkUsernameAvailability(this);
    });

    $(usernameField).on('keydown', function handleUsernameEntry() {
      const usernamefield = this;
      if (typingTimerUsername) clearTimeout(typingTimerUsername);
      typingTimerUsername = setTimeout(() => {
        checkUsernameAvailability(usernamefield);
      }, typingWaitInterval);
    });
  }

  if (passwordForm) {
    $(passwordField).on('change', function handlePasswordFieldChange() {
      checkPasswordStrength(this);
    });

    $(passwordField).on('keydown', function handlePasswordEntry() {
      const field = this;
      if (typingTimer) clearTimeout(typingTimer);
      typingTimer = setTimeout(() => {
        checkPasswordStrength(field);
      }, typingWaitInterval);
    });

    $(passwordForm).find('button[type="submit"]').attr('disabled', true);
    $(passwordField).on('keydown', function validatePasswordField() {
      $(this).parsley().validate();
    });

    $(passwordForm)
      .parsley()
      .subscribe('parsley:field:validated', () => {
        if (
          $(passwordForm).parsley().isValid() &&
          $(passwordForm).hasClass('password-valid')
        ) {
          $(passwordForm).find('button[type="submit"]').attr('disabled', false);
        } else {
          $(passwordForm).find('button[type="submit"]').attr('disabled', true);
        }
      });
  }
};
