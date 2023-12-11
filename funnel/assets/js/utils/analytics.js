/* global gtag */
const Analytics = {
  sendToGA(category, action, label = '', value = 0) {
    if (typeof ga !== 'undefined') {
      gtag('event', category, {
        event_category: action,
        event_label: label,
        value,
      });
    }
  },
  init() {
    // Send click events to Google analytics
    $('.mui-btn, a').click(function gaHandler() {
      const action =
        $(this).attr('data-ga') || $(this).attr('title') || $(this).html();
      const target = $(this).attr('data-target') || $(this).attr('href') || '';
      Analytics.sendToGA('click', action, target);
    });
    $('.ga-login-btn').click(function gaHandler() {
      const action = $(this).attr('data-ga');
      Analytics.sendToGA('login', action);
    });
    $('.search-form__submit').click(function gaHandler() {
      const target = $('.js-search-field').val();
      Analytics.sendToGA('search', target, target);
    });
  },
};

export default Analytics;
