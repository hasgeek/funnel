/* global grecaptcha */
import Form from './utils/formhelper';

$(() => {
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
});
