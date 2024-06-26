import 'jquery-modal';
import 'trunk8';
import pace from 'pace-js';

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
import './utils/getDevicePixelRatio';
import setTimezoneCookie from './utils/timezone';
import './utils/follow_action';
import 'muicss/dist/js/mui';

$(() => {
  /* eslint-disable no-console */
  console.log(
    'Hello, curious geek. Our source is at https://github.com/hasgeek. Why not contribute a patch?',
  );

  loadLangTranslations();
  window.Hasgeek.Config.errorMsg = {
    serverError: window.gettext(
      'An internal server error occurred. Our support team has been notified and will investigate',
    ),
    networkError: window.gettext(
      'Unable to connect. Check connection and refresh the page',
    ),
    rateLimitError: window.gettext('This is unusually high activity. Try again later'),
    error: window.gettext('An error occurred when submitting the form'),
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

  setTimezoneCookie();
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
