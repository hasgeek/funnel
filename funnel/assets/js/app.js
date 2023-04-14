/* global jstz, Pace */

import Utils from './utils/helper';
import ScrollHelper from './utils/scrollhelper';
import loadLangTranslations from './utils/translations';
import LazyloadImg from './utils/lazyloadimage';
import Form from './utils/formhelper';
import Analytics from './utils/analytics';
import Tabs from './utils/tabs';

$(() => {
  // Code notice
  console.log(
    'Hello, curious geek. Our source is at https://github.com/hasgeek. Why not contribute a patch?'
  );

  window.Hasgeek.Config.availableLanguages = {
    en: 'en_IN',
    hi: 'hi_IN',
  };
  window.Hasgeek.Config.mobileBreakpoint = 768; // this breakpoint switches to desktop UI
  window.Hasgeek.Config.ajaxTimeout = 30000;
  window.Hasgeek.Config.retryInterval = 10000;
  window.Hasgeek.Config.closeModalTimeout = 10000;
  window.Hasgeek.Config.refreshInterval = 60000;
  window.Hasgeek.Config.notificationRefreshInterval = 300000;
  window.Hasgeek.Config.readReceiptTimeout = 5000;
  window.Hasgeek.Config.saveEditorContentTimeout = 300;
  window.Hasgeek.Config.userAvatarImgSize = {
    big: '160',
    medium: '80',
    small: '48',
  };
  window.Hasgeek.Config.defaultLatitude = '12.961443';
  window.Hasgeek.Config.defaultLongitude = '77.64435000000003';
  window.Hasgeek.Config.errorMsg = {
    serverError: window.gettext(
      'An internal server error occurred. Our support team has been notified and will investigate'
    ),
    networkError: window.gettext(
      'Unable to connect. Check connection and refresh the page'
    ),
    rateLimitError: window.gettext('This is unusually high activity. Try again later'),
    error: window.gettext('An error occured when submitting the form'),
  };

  loadLangTranslations();
  Utils.collapse();
  ScrollHelper.smoothScroll();
  Utils.navSearchForm();
  Utils.headerMenuDropdown(
    '.js-menu-btn',
    '.js-account-menu-wrapper',
    '.js-account-menu',
    window.Hasgeek.Config.accountMenu
  );
  ScrollHelper.scrollTabs();
  Tabs.init();
  Utils.truncate();
  Utils.showTimeOnCalendar();
  Utils.popupBackHandler();
  Form.handleModalForm();

  window.Hasgeek.activate_select2 = Form.activate_select2.bind(Form);

  if ($('.header__nav-links--updates').length) {
    Utils.updateNotificationStatus();
    window.setInterval(
      Utils.updateNotificationStatus,
      window.Hasgeek.Config.notificationRefreshInterval
    );
  }
  Utils.addWebShare();
  if (window.Hasgeek.Config.commentSidebarElem) {
    Utils.headerMenuDropdown(
      '.js-comments-btn',
      '.js-comments-wrapper',
      '.js-comment-sidebar',
      window.Hasgeek.Config.unreadCommentUrl
    );
  }
  Utils.sendNotificationReadStatus();

  const intersectionObserverComponents = function intersectionObserverComponents() {
    LazyloadImg.init('js-lazyload-img');
  };

  if (
    document.querySelector('.js-lazyload-img') ||
    document.querySelector('.js-lazyload-results')
  ) {
    if (
      !(
        'IntersectionObserver' in global &&
        'IntersectionObserverEntry' in global &&
        'intersectionRatio' in IntersectionObserverEntry.prototype
      )
    ) {
      const polyfill = document.createElement('script');
      polyfill.setAttribute('type', 'text/javascript');
      polyfill.setAttribute(
        'src',
        'https://cdn.polyfill.io/v2/polyfill.min.js?features=IntersectionObserver'
      );
      polyfill.onload = function loadintersectionObserverComponents() {
        intersectionObserverComponents();
      };
      document.head.appendChild(polyfill);
    } else {
      intersectionObserverComponents();
    }
  }

  if (!('URLSearchParams' in window)) {
    const polyfill = document.createElement('script');
    polyfill.setAttribute('type', 'text/javascript');
    polyfill.setAttribute(
      'src',
      'https://cdnjs.cloudflare.com/ajax/libs/url-search-params/1.1.0/url-search-params.js'
    );
    document.head.appendChild(polyfill);
  }

  // Send click events to Google analytics
  $('.mui-btn, a').click(function gaHandler() {
    const action = $(this).attr('data-ga') || $(this).attr('title') || $(this).html();
    const target = $(this).attr('data-target') || $(this).attr('href') || '';
    Analytics.sendToGA('click', action, target);
  });
  $('.search-form__submit').click(function gaHandler() {
    const target = $('.js-search-field').val();
    Analytics.sendToGA('search', target, target);
  });

  // Detect timezone for login
  if ($.cookie('timezone') === null) {
    $.cookie('timezone', jstz.determine().name(), { path: '/' });
  }

  // Override Parsley.js's default messages after the page loads.
  // Our versions don't use full stops after phrases.
  window.ParsleyConfig = {
    errorsWrapper: '<div></div>',
    errorTemplate: '<p class="mui-form__error"></p>',
    errorClass: 'has-error',
    classHandler(ParsleyField) {
      return ParsleyField.$element.closest('.mui-form__fields');
    },
    errorsContainer(ParsleyField) {
      return ParsleyField.$element.closest('.mui-form__controls');
    },
    i18n: {
      en: {},
    },
  };

  window.ParsleyConfig.i18n.en = $.extend(window.ParsleyConfig.i18n.en || {}, {
    defaultMessage: 'This value seems to be invalid',
    notblank: 'This value should not be blank',
    required: 'This value is required',
    pattern: 'This value seems to be invalid',
    min: 'This value should be greater than or equal to %s',
    max: 'This value should be lower than or equal to %s',
    range: 'This value should be between %s and %s',
    minlength: 'This value is too short. It should have %s characters or more',
    maxlength: 'This value is too long. It should have %s characters or fewer',
    length: 'This value should be between %s and %s characters long',
    mincheck: 'You must select at least %s choices',
    maxcheck: 'You must select %s choices or fewer',
    check: 'You must select between %s and %s choices',
    equalto: 'This value should be the same',
  });
  window.ParsleyConfig.i18n.en.type = $.extend(
    window.ParsleyConfig.i18n.en.type || {},
    {
      email: 'This value should be a valid email',
      url: 'This value should be a valid url',
      number: 'This value should be a valid number',
      integer: 'This value should be a valid integer',
      digits: 'This value should be digits',
      alphanum: 'This value should be alphanumeric',
    }
  );

  const csrfRefresh = function () {
    $.ajax({
      type: 'GET',
      url: '/api/baseframe/1/csrf/refresh',
      timeout: 5000,
      dataType: 'json',
      success(data) {
        $('meta[name="csrf-token"]').attr('content', data.csrf_token);
        $('input[name="csrf_token"]').val(data.csrf_token);
      },
    });
  };

  // Request for new CSRF token and update the page every 15 mins
  setInterval(csrfRefresh, 900000);

  $('body').on('click', '.alert__close', function () {
    $(this).parents('.alert').fadeOut();
  });
});

if (
  navigator.userAgent.match(/(iPhone|Android)/) &&
  !(
    window.navigator.standalone === true ||
    window.matchMedia('(display-mode: standalone)').matches
  )
) {
  $('.pace').addClass('pace-hide');
  window.onbeforeunload = function stopPace() {
    Pace.stop();
  };
}
