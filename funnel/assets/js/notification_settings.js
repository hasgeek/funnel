import { Utils } from './util';

$(() => {
  window.Hasgeek.NotificationSettings = function (config) {
    $('.js-toggle-switch').on('change', function () {
      let checkbox = $(this);
      let transport = $(this).attr('id');
      let currentState = this.checked;
      let previousState = !currentState;
      $.ajax({
        type: 'POST',
        url: config.url,
        data: $(this).parents('.js-autosubmit-form').serializeArray(),
        dataType: 'json',
        timeout: window.Hasgeek.config.ajaxTimeout,
        success: function () {
          if (currentState && transport) {
            $(`input[data-transport="preference-${transport}"]`).attr(
              'disabled',
              false
            );
            $(`label[data-transport="preference-${transport}"]`).removeClass(
              'switch-label--disabled'
            );
          } else if (transport) {
            $(`input[data-transport="preference-${transport}"]`).attr(
              'disabled',
              true
            );
            $(`label[data-transport="preference-${transport}"]`).addClass(
              'switch-label--disabled'
            );
          }
        },
        error: function (response) {
          Utils.handleAjaxError(response);
          $(checkbox).prop('checked', previousState);
        },
      });
    });
  };
});
