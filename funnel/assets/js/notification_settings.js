import Form from './utils/formhelper';

$(() => {
  window.Hasgeek.notificationSettings = (config) => {
    $('.js-toggle-switch').on('change', function toggleNotifications() {
      const checkbox = $(this);
      const transport = $(this).attr('id');
      const currentState = this.checked;
      const previousState = !currentState;
      const form = $(this).parents('.js-autosubmit-form')[0];
      fetch(config.url, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: new URLSearchParams(new FormData(form)).toString(),
      })
        .then(() => {
          if (currentState && transport) {
            $(`input[data-transport="preference-${transport}"]`).attr(
              'disabled',
              false
            );
            $(`label[data-transport="preference-${transport}"]`).removeClass(
              'switch-label--disabled'
            );
          } else if (transport) {
            $(`input[data-transport="preference-${transport}"]`).attr('disabled', true);
            $(`label[data-transport="preference-${transport}"]`).addClass(
              'switch-label--disabled'
            );
          }
        })
        .catch((error) => {
          Form.handleAjaxError(error);
          $(checkbox).prop('checked', previousState);
        });
    });
  };
});
