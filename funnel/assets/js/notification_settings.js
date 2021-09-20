import Form from './utils/formhelper';

$(() => {
  window.Hasgeek.notificationSettings = (config) => {
    $('.js-toggle-switch').on('change', function toggleNotifications() {
      const checkbox = $(this);
      const transport = $(this).attr('id');
      const currentState = this.checked;
      const previousState = !currentState;
      $.ajax({
        type: 'POST',
        url: config.url,
        data: $(this).parents('.js-autosubmit-form').serializeArray(),
        dataType: 'json',
        timeout: window.Hasgeek.Config.ajaxTimeout,
        success() {
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
        error(response) {
          Form.handleAjaxError(response);
          $(checkbox).prop('checked', previousState);
        },
      });
    });
  };
});
