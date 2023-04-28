import 'jquery-modal';
import 'trunk8';
import jstz from 'jstz';
import 'jquery.cookie';
import Utils from './utils/helper';
import WebShare from './utils/webshare';
import ScrollHelper from './utils/scrollhelper';
import loadLangTranslations from './utils/translations';
import LazyloadImg from './utils/lazyloadimage';
import Modal from './utils/modalhelper';
import Analytics from './utils/analytics';
import Tabs from './utils/tabs';
import updateParsleyConfig from './utils/update_parsley_config';
import ReadStatus from './utils/read_status';
import LazyLoadMenu from './utils/lazyloadmenu';

const pace = require('pace-js');

$(() => {
  // Code notice
  console.log(
    'Hello, curious geek. Our source is at https://github.com/hasgeek. Why not contribute a patch?'
  );

  loadLangTranslations();
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

  Utils.collapse();
  ScrollHelper.smoothScroll();
  Utils.navSearchForm();
  ScrollHelper.scrollTabs();
  Tabs.init();
  Utils.truncate();
  Utils.showTimeOnCalendar();
  Modal.addUsability();
  Analytics.init();
  WebShare.addWebShare();
  ReadStatus.init();
  LazyLoadMenu.init();
  LazyloadImg.init('js-lazyload-img');
  // Request for new CSRF token and update the page every 15 mins
  setInterval(Utils.csrfRefresh, 900000);

  // Add polyfill
  if (!('URLSearchParams' in window)) {
    const polyfill = document.createElement('script');
    polyfill.setAttribute('type', 'text/javascript');
    polyfill.setAttribute(
      'src',
      'https://cdnjs.cloudflare.com/ajax/libs/url-search-params/1.1.0/url-search-params.js'
    );
    document.head.appendChild(polyfill);
  }

  // Detect timezone for login
  if ($.cookie('timezone') === null) {
    $.cookie('timezone', jstz.determine().name(), { path: '/' });
  }

  updateParsleyConfig();
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
    pace.stop();
  };
}
