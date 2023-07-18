import toastr from 'toastr';
import Form from './utils/formhelper';
import ScrollHelper from './utils/scrollhelper';

$(() => {
  window.Hasgeek.notificationSettings = (config) => {
    let [tab] = config.tabs;
    const headerHeight =
      ScrollHelper.getPageHeaderHeight() + $('.tabs-wrapper').height();
    if (window.location.hash) {
      const urlHash = window.location.hash.split('#').pop();
      config.tabs.forEach((tabVal) => {
        if (urlHash.includes(tabVal)) {
          tab = tabVal;
        }
      });
    } else {
      window.location.hash = tab;
    }
    ScrollHelper.animateScrollTo($(`#${tab}`).offset().top - headerHeight);
    $(`.js-pills-tab-${tab}`).addClass('mui--is-active');
    $(`.js-pills-tab-${tab}`).find('a').attr('tabindex', 1).attr('aria-selected', true);
    $(`.js-tabs-pane-${tab}`).addClass('mui--is-active');

    $('.js-tab-anchor').on('click', function scrollToTabpane() {
      const tabPane = $('.js-tab-anchor').attr('href');
      ScrollHelper.animateScrollTo($(tabPane).offset().top - headerHeight);
    });

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
          const errorMsg = Form.handleAjaxError(error);
          toastr.error(errorMsg);
          $(checkbox).prop('checked', previousState);
        });
    });
  };
});
