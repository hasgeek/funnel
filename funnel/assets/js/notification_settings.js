import { Utils } from './util';

$(() => {
  window.Hasgeek.NotificationSettings = function (config) {
    $('.js-toggle-switch').on('change', function () {
      var checkbox = $(this);
      var state = !this.checked;
      $.ajax({
        type: 'POST',
        url: config.url,
        data: $(this).parents('.js-autosubmit-form').serializeArray(),
        dataType: 'json',
        timeout: window.Hasgeek.config.ajaxTimeout,
        error: function (response) {
          console.log('error');
          Utils.handleAjaxError(response);
          $(checkbox).prop('checked', state);
        },
      });
    });
  };
});
