/* global grecaptcha */
import { activateFormWidgets, MapMarker } from './utils/form_widgets';
import Form from './utils/formhelper';

window.Hasgeek.initWidgets = async function init(fieldName, config) {
  switch (fieldName) {
    case 'AutocompleteField': {
      const { default: widget } = await import('./utils/autocomplete_widget');
      widget.textAutocomplete(config);
      break;
    }
    case 'ImgeeField':
      window.addEventListener('message', (event) => {
        if (event.origin === config.host) {
          const message = JSON.parse(event.data);
          if (message.context === 'imgee.upload') {
            $(`#imgee-loader-${config.fieldId}`).removeClass('mui--hide');
            $(`#img_${config.fieldId}`).attr('src', message.embed_url);
            $(`#${config.fieldId}`).val(message.embed_url);
            if (config.widgetType) $.modal.close();
          }
        }
      });
      $(`#img_${config.fieldId}`).on('load', () => {
        $(`#imgee-loader-${config.fieldId}`).addClass('mui--hide');
      });
      break;
    case 'UserSelectField': {
      const { default: lastUserWidget } = await import('./utils/autocomplete_widget');
      lastUserWidget.lastuserAutocomplete(config);
      break;
    }
    case 'GeonameSelectField': {
      const { default: geonameWidget } = await import('./utils/autocomplete_widget');
      geonameWidget.geonameAutocomplete(config);
      break;
    }
    case 'CoordinatesField':
      /* eslint-disable no-new */
      await import('jquery-locationpicker');
      new MapMarker(config);
      break;
    default:
      break;
  }
};

window.Hasgeek.preventDoubleSubmit = function (formId, isXHR, alertBoxHtml) {
  if (isXHR) {
    document.body.addEventListener('htmx:beforeSend', () => {
      Form.preventDoubleSubmit(formId);
    });
    document.body.addEventListener('htmx:responseError', (event) => {
      Form.showFormError(formId, event.detail.xhr, alertBoxHtml);
    });
  } else {
    $(() => {
      // Disable submit button when clicked. Prevent double click.
      $(`#${formId}`).submit(function () {
        if (
          !$(this).data('parsley-validate') ||
          ($(this).data('parsley-validate') && $(this).hasClass('parsley-valid'))
        ) {
          $(this).find('button[type="submit"]').prop('disabled', true);
          $(this).find('input[type="submit"]').prop('disabled', true);
          $(this).find('.loading').removeClass('mui--hide');
        }
      });
    });
  }
};

window.Hasgeek.recaptcha = function (formId, formWrapperId, ajax, alertBoxHtml) {
  if (ajax) {
    window.onInvisibleRecaptchaSubmit = function () {
      const postUrl = $(`#${formId}`).attr('action');
      const onSuccess = function (responseData) {
        $(`#${formWrapperId}`).html(responseData); // Replace with OTP form received as response
      };
      const onError = function (response) {
        Form.showFormError(formId, response, alertBoxHtml);
      };
      Form.ajaxFormSubmit(formId, postUrl, onSuccess, onError, {
        dataType: 'html',
      });
    };
    document.getElementById(formId).onsubmit = function (event) {
      event.preventDefault();
      grecaptcha.execute();
    };
  } else {
    window.onInvisibleRecaptchaSubmit = function () {
      document.getElementById(formId).submit();
    };
    document.getElementById(formId).onsubmit = function (event) {
      event.preventDefault();
      if (typeof grecaptcha !== 'undefined' && grecaptcha.getResponse() === '') {
        grecaptcha.execute();
      } else {
        document.getElementById(formId).submit();
      }
    };
  }
};

$(() => {
  activateFormWidgets();
});
