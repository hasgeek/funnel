/* global gettext, vegaEmbed */

import Gettext from './gettext';
import * as timeago from 'timeago.js';
/*eslint camelcase: ["error", {allow: ["hi_IN"]}]*/
import hi_IN from 'timeago.js/lib/lang/hi_IN';

/* global ga */
export const Utils = {
  // convert array of objects into hashmap
  tohashMap(objectArray, key) {
    const hashMap = {};
    objectArray.forEach((obj) => {
      hashMap[obj[key]] = obj;
    });
    return hashMap;
  },
  findLoopIndex(objectArray, key, search) {
    let index;

    for (index = 0; index < objectArray.length; index += 1) {
      if (objectArray[index][key] === search) {
        break;
      }
    }

    return index;
  },
  collapse() {
    $('.collapsible__header').on('click', function collapseContent() {
      $(this).find('.collapsible__icon').toggleClass('mui--hide');
      $(this).siblings('.collapsible__body').slideToggle();
    });
  },
  animateScrollTo(offsetY) {
    $('html,body').animate(
      {
        scrollTop: offsetY,
      },
      'slow'
    );
  },
  smoothScroll() {
    $('a.js-smooth-scroll').on('click', function clickHandler() {
      Utils.animateScrollTo($(this.hash).offset().top);
    });
  },
  scrollTabs() {
    if (document.getElementById('jquery-scroll-tabs')) {
      // Horizontal scroll to active tab
      $('#jquery-scroll-tabs').animate(
        {
          scrollLeft: document.querySelector('.tabs__item--active').offsetLeft,
        },
        'slow'
      );
      $('#jquery-scroll-tabs .js-scroll-prev').on('click', (event) => {
        event.preventDefault();
        const prevTab = $('.tabs__item--active')
          .prev('.tabs__item')
          .attr('href');

        if (prevTab) {
          window.location.href = prevTab;
        }
      });
      $('#jquery-scroll-tabs .js-scroll-next').on('click', (event) => {
        event.preventDefault();
        const nextTab = $('.tabs__item--active')
          .next('.tabs__item')
          .attr('href');

        if (nextTab) {
          window.location.href = nextTab;
        }
      });
    }
  },
  navSearchForm() {
    $('.js-search-show').on('click', function toggleSearchForm(event) {
      event.preventDefault();
      $('.js-search-form').toggleClass('search-form--show');
      $('.js-search-field').focus();
    }); // Clicking outside close search form if open

    $('body').on('click', function closeSearchForm(event) {
      if (
        $('.js-search-form').hasClass('search-form--show') &&
        !$(event.target).is('.js-search-field') &&
        !$.contains($('.js-search-show')[0], event.target)
      ) {
        $('.js-search-form').removeClass('search-form--show');
      }
    });
  },
  headerMenuDropdown(menuBtnClass, menuWrapper, menu, url) {
    let menuBtn = $(menuBtnClass);
    let topMargin = 1;
    let headerHeight = $('.header').height() + topMargin;
    let page = 1;
    let lazyLoader;
    let observer;

    let openMenu = function () {
      if ($(window).width() < window.Hasgeek.config.mobileBreakpoint) {
        $(menuWrapper).find(menu).animate({ top: '0' });
      } else {
        $(menuWrapper).find(menu).animate({ top: headerHeight });
      }
      $('.header__nav-links--active').addClass('header__nav-links--menuOpen');
      menuBtn.addClass('header__nav-links--active');
      $('body').addClass('body-scroll-lock');
    };

    let closeMenu = function () {
      if ($(window).width() < window.Hasgeek.config.mobileBreakpoint) {
        $(menuWrapper).find(menu).animate({ top: '100vh' });
      } else {
        $(menuWrapper).find(menu).animate({ top: '-100vh' });
      }
      menuBtn.removeClass('header__nav-links--active');
      $('body').removeClass('body-scroll-lock');
      $('.header__nav-links--active').removeClass(
        'header__nav-links--menuOpen'
      );
    };

    let updatePageNumber = function () {
      page += 1;
    };

    let fetchMenu = function (pageNo = 1) {
      $.ajax({
        type: 'GET',
        url: `${url}?page=${pageNo}`,
        timeout: window.Hasgeek.config.ajaxTimeout,
        success: function (responseData) {
          $(menuWrapper).find(menu).append(responseData);
          updatePageNumber();
          lazyLoader = document.querySelector('.js-load-comments');
          if (lazyLoader) {
            observer = new IntersectionObserver(
              function (entries) {
                entries.forEach((entry) => {
                  if (entry.isIntersecting) {
                    observer.unobserve(lazyLoader);
                    $('.js-load-comments').remove();
                    fetchMenu(page);
                  }
                });
              },
              {
                rootMargin: '0px',
                threshold: 0,
              }
            );
            observer.observe(lazyLoader);
          }
        },
      });
    };

    //If user logged in, preload menu
    if ($(menuWrapper).length) {
      fetchMenu();
    }

    // Open full screen account menu in mobile
    menuBtn.on('click', function () {
      if ($(this).hasClass('header__nav-links--active')) {
        closeMenu();
      } else {
        openMenu();
      }
    });

    $('body').on('click', function (event) {
      let totalBtn = $(menuBtn).toArray();
      let isChildElem = false;
      totalBtn.forEach(function (element) {
        isChildElem = isChildElem || $.contains(element, event.target);
      });
      if (
        $(menuBtn).hasClass('header__nav-links--active') &&
        !$(event.target).is(menuBtn) &&
        !isChildElem
      ) {
        closeMenu();
      }
    });
  },
  sendToGA(category, action, label, value = 0) {
    if (typeof ga !== 'undefined') {
      ga('send', {
        hitType: 'event',
        eventCategory: category,
        eventAction: action,
        eventLabel: label,
        eventValue: value,
      });
    }
  },
  truncate() {
    let readMoreTxt = `&hellip;<span class="js-read-more mui--text-hyperlink read-more">${gettext(
      'read more'
    )}</span>`;

    $('.js-truncate').each(function () {
      let linesLimit = $(this).data('truncate-lines');
      $(this).trunk8({
        lines: linesLimit,
      });
    });

    $('.js-truncate-readmore').each(function () {
      let linesLimit = $(this).data('truncate-lines');
      $(this).trunk8({
        lines: linesLimit,
        fill: readMoreTxt,
        parseHTML: true,
      });
    });

    $('body').on('click', '.js-read-more', function () {
      $(this).parent('.js-truncate-readmore').trunk8('revert');
    });
  },
  showTimeOnCalendar() {
    const singleDay = 24 * 60 * 60 * 1000;

    $('body .card__calendar').each(function () {
      let firstActiveWeek = $(this).find('.calendar__weekdays__dates--upcoming')
        .length
        ? $(this).find('.calendar__weekdays__dates--upcoming--first')
        : $(this).find('.calendar__weekdays__dates--latest');

      firstActiveWeek
        .find(
          '.calendar__weekdays__dates__date--showtime.calendar__weekdays__dates__date--latest:first'
        )
        .addClass('calendar__weekdays__dates__date--display');

      $(this)
        .find('.calendar__weekdays__dates__date--showtime')
        .hover(function () {
          $(this)
            .parents('.calendar__weekdays')
            .find('.calendar__weekdays__dates__date--showtime')
            .removeClass('calendar__weekdays__dates__date--display');
        });

      $(this)
        .find('.calendar__weekdays__dates__date--showtime')
        .mouseleave(function () {
          firstActiveWeek
            .find(
              '.calendar__weekdays__dates__date--showtime.calendar__weekdays__dates__date--latest:first'
            )
            .addClass('calendar__weekdays__dates__date--display');
        });

      let todayDate = $(this).find('.calendar__month__counting').data('today');
      let nextEventElem = $(this)
        .find('.calendar__weekdays__dates--upcoming--first')
        .first()
        .find(
          '.calendar__weekdays__dates__date--showtime.calendar__weekdays__dates__date--latest'
        )
        .first();
      let eventDate = nextEventElem.data('event-date');
      let eventMonth = nextEventElem.data('event-month');
      let monthElem = $(this)
        .find('.calendar__month')
        .find("[data-month='" + eventMonth + "']");

      // Today's date in terms of number of milliseconds since January 1, 1970, 00:00:00 UTC
      let today = Date.parse(todayDate);
      // Event date in terms of number of milliseconds since January 1, 1970, 00:00:00 UTC
      let eventDay = Date.parse(eventDate);
      // Find the difference between event and today's date in UTC
      let counting = Math.round((eventDay - today) / singleDay);
      // Defined these strings in project_countdown macro in calendar_snippet.js.jinja2
      let dayText = [
        gettext('Today'),
        gettext('Tomorrow'),
        gettext('Day after'),
        gettext('In %d days', counting),
      ];
      // Show number of days on the widget only if it is less than 32 days
      if (counting >= 0 && counting < 3) {
        monthElem.text(dayText[counting]);
      } else if (counting > 2 && counting < 32) {
        monthElem.text(dayText[3]);
      }
    });
  },
  getElementId(htmlString) {
    return htmlString.match(/id="(.*?)"/)[1];
  },
  getResponseError(response) {
    let errorMsg = '';

    // Add server error strings for translations in server_error.js.jinja2
    if (response.readyState === 4) {
      if (response.status === 500) {
        errorMsg = window.Hasgeek.config.errorMsg.serverError;
      } else if (
        response.status === 422 &&
        response.responseJSON.error === 'requires_sudo'
      ) {
        window.location.href = `${
          window.Hasgeek.config.accountSudo
        }?next=${encodeURIComponent(window.location.href)}`;
      } else {
        errorMsg = response.responseJSON.error_description;
      }
    } else {
      errorMsg = window.Hasgeek.config.errorMsg.networkError;
    }
    return errorMsg;
  },
  handleAjaxError(errorResponse) {
    Utils.updateFormNonce(errorResponse.responseJSON);
    let errorMsg = Utils.getResponseError(errorResponse);
    window.toastr.error(errorMsg);
    return errorMsg;
  },
  formErrorHandler(formId, errorResponse) {
    $(`#${formId}`).find('button[type="submit"]').attr('disabled', false);
    $(`#${formId}`).find('.loading').addClass('mui--hide');
    return Utils.handleAjaxError(errorResponse);
  },
  getActionUrl(formId) {
    return $(`#${formId}`).attr('action');
  },
  updateFormNonce(response) {
    if (response && response.form_nonce) {
      $('input[name="form_nonce"]').val(response.form_nonce);
    }
  },
  popupBackHandler() {
    $('.js-popup-back').on('click', function (event) {
      if (document.referrer !== '') {
        event.preventDefault();
        window.history.back();
      }
    });
  },
  handleModalForm() {
    $('.js-modal-form').click(function () {
      window.location.hash = $(this).data('hash');
    });

    $('body').on($.modal.BEFORE_CLOSE, () => {
      if (window.location.hash) {
        window.history.replaceState(
          '',
          '',
          window.location.pathname + window.location.search
        );
      }
    });

    window.addEventListener(
      'hashchange',
      function () {
        if (window.location.hash === '') {
          $.modal.close();
        }
      },
      false
    );

    let hashId = window.location.hash.split('#')[1];
    if (hashId) {
      if ($('a.js-modal-form[data-hash="' + hashId + '"]').length) {
        $('a[data-hash="' + hashId + '"]').click();
      }
    }
  },
  setNotifyIcon(unread) {
    if (unread) {
      $('.header__nav-links--updates').addClass(
        'header__nav-links--updates--unread'
      );
    } else {
      $('.header__nav-links--updates').removeClass(
        'header__nav-links--updates--unread'
      );
    }
  },
  updateNotificationStatus() {
    $.ajax({
      type: 'GET',
      url: window.Hasgeek.config.notificationCount,
      dataType: 'json',
      timeout: window.Hasgeek.config.ajaxTimeout,
      success: function (responseData) {
        Utils.setNotifyIcon(responseData.unread);
      },
    });
  },
  addWebShare() {
    if (navigator.share) {
      $('.project-links').hide();
      $('.hg-link-btn').removeClass('mui--hide');

      $('body').on('click', '.hg-link-btn', function (event) {
        event.preventDefault();
        navigator.share({
          title: $(this).data('title') || document.title,
          url:
            $(this).data('url') ||
            (document.querySelector('link[rel=canonical]') &&
              document.querySelector('link[rel=canonical]').href) ||
            window.location.href,
          text: $(this).data('text') || '',
        });
      });
    } else {
      $('body').on('click', '.js-copy-link', function (event) {
        event.preventDefault();
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents($(this).find('.js-copy-url')[0]);
        selection.removeAllRanges();
        selection.addRange(range);
        document.execCommand('copy');
        window.toastr.success(gettext('Link copied'));
        selection.removeAllRanges();
      });
    }
  },
  enableWebShare() {
    if (navigator.share) {
      $('.project-links').hide();
      $('.hg-link-btn').removeClass('mui--hide');
    }
  },
  getPageHeaderHeight() {
    let headerHeight;
    if ($(window).width() < window.Hasgeek.config.mobileBreakpoint) {
      headerHeight = $('.mobile-nav').height();
    } else {
      headerHeight = $('header').height() + $('nav').height();
    }
    return headerHeight;
  },
  getLocale() {
    // Instantiate i18n with browser context
    let lang = document.documentElement.lang;
    let langShortForm = lang.substring(0, 2);
    window.Hasgeek.config.locale =
      window.Hasgeek.config.availableLanguages[langShortForm];
    return window.Hasgeek.config.locale;
  },
  loadLangTranslations() {
    Utils.getLocale();

    window.i18n = new Gettext({
      translatedLang: window.Hasgeek.config.locale,
    });
    window.gettext = window.i18n.gettext.bind(window.i18n);
    window.ngettext = window.i18n.ngettext.bind(window.i18n);
  },
  getTimeago() {
    // en_US and zh_CN are built in timeago, other languages requires to be registered.
    timeago.register('hi_IN', hi_IN);
    return timeago;
  },
  activateToggleSwitch() {
    $('.js-toggle').on('change', function () {
      let checkbox = $(this);
      let currentState = this.checked;
      let previousState = !currentState;
      let formData = $(checkbox).parent('form').serializeArray();
      if (!currentState) {
        formData.push({ name: $(this).attr('name'), value: 'false' });
      }
      $.ajax({
        type: 'POST',
        url: $(checkbox).parent('form').attr('action'),
        data: formData,
        dataType: 'json',
        timeout: window.Hasgeek.config.ajaxTimeout,
        success: function (responseData) {
          if (responseData && responseData.message) {
            window.toastr.success(responseData.message);
          }
        },
        error: function (response) {
          Utils.handleAjaxError(response);
          $(checkbox).prop('checked', previousState);
        },
      });
    });

    $('.js-dropdown-toggle').on('click', function (event) {
      event.stopPropagation();
    });
  },
  addVegaSupport() {
    if ($('.language-vega-lite').length > 0) {
      let vegaliteCDN = [
        'https://cdn.jsdelivr.net/npm/vega@5',
        'https://cdn.jsdelivr.net/npm/vega-lite@5',
        'https://cdn.jsdelivr.net/npm/vega-embed@6',
      ];
      let vegaliteUrl = 0;
      let loadVegaScript = function () {
        $.getScript({ url: vegaliteCDN[vegaliteUrl], cache: true }).success(
          function () {
            if (vegaliteUrl < vegaliteCDN.length) {
              vegaliteUrl += 1;
              loadVegaScript();
            }
            // Once all vega js is loaded, initialize vega visualization on all pre tags with class 'language-vega-lite'
            if (vegaliteUrl === vegaliteCDN.length) {
              $('.language-vega-lite').each(function () {
                vegaEmbed(this, JSON.parse($(this).find('code').text()), {
                  renderer: 'svg',
                  actions: {
                    source: false,
                    editor: false,
                    compiled: false,
                  },
                });
              });
            }
          }
        );
      };
      loadVegaScript();
    }
  },
};

export const ScrollActiveMenu = {
  init(navId, navItemsClassName, activeMenuClassName) {
    this.navId = navId;
    this.navItemsClassName = navItemsClassName;
    this.activeMenuClassName = activeMenuClassName;
    this.navItems = [...document.querySelectorAll(`.${navItemsClassName}`)];
    this.headings = this.navItems.map((navItem) => {
      if (navItem.classList.contains('js-samepage')) {
        return document.querySelector(navItem.getAttribute('href'));
      }

      return false;
    });
    this.handleObserver = this.handleObserver.bind(this);
    this.headings.forEach((heading) => {
      if (heading) {
        const threshold =
          heading.offsetHeight / window.innerHeight > 1
            ? 0.1
            : heading.offsetHeight / window.innerHeight;
        const observer = new IntersectionObserver(this.handleObserver, {
          rootMargin: '0px',
          threshold,
        });
        observer.observe(heading);
      }
    });
    this.activeNavItem = '';
  },

  handleObserver(entries) {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const activeNavItem = this.navItems.find(
          (navItem) =>
            navItem.getAttribute('href') ===
            `#${entry.target.getAttribute('id')}`
        );
        this.setActiveNavItem(activeNavItem);
      }
    });
  },

  setActiveNavItem(activeNavItem) {
    this.activeNavItem = activeNavItem;
    $(`.${this.navItemsClassName}`).removeClass(this.activeMenuClassName);
    activeNavItem.classList.add(this.activeMenuClassName);
    $(`#${this.navId}`).animate(
      {
        scrollLeft: activeNavItem.offsetLeft,
      },
      'slow'
    );
  },
};
export const LazyloadImg = {
  init(imgClassName) {
    this.imgItems = [...document.querySelectorAll(`.${imgClassName}`)];
    this.imgItems.forEach((img) => {
      if (img) {
        let observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                entry.target.src = entry.target.dataset.src;
                observer = observer.disconnect();
              }
            });
          },
          {
            rootMargin: '0px',
            threshold: 0,
          }
        );
        observer.observe(img);
      }
    });
  },
};
export const SaveProject = function ({
  formId,
  postUrl = $(`#${formId}`).attr('action'),
  config = {},
}) {
  const onSuccess = function (response) {
    $(`#${formId}`)
      .find('button')
      .prop('disabled', false)
      .removeClass('animate-btn--animate');

    $(`#${formId}`)
      .find('button')
      .each(function () {
        if ($(this).hasClass('animate-btn--show')) {
          $(this).removeClass('animate-btn--show');
        } else {
          $(this).addClass('animate-btn--show');
          if ($(this).hasClass('animate-btn--saved')) {
            $(this).addClass('animate-btn--animate');
            window.toastr.success(
              gettext('Project added to Account > Saved projects')
            );
          }
        }
      });
    Utils.updateFormNonce(response);
  };

  const onError = function (response) {
    return Utils.handleAjaxError(response);
  };

  window.Baseframe.Forms.handleFormSubmit(
    formId,
    postUrl,
    onSuccess,
    onError,
    config
  );
};

export const Video = {
  /* Takes argument
     `videoWrapper`: video container element,
     'videoUrl': video url
    Video id is extracted from the video url (getVideoTypeAndId).
    The videoID is then used to generate the iframe html.
    The generated iframe is added to the video container element.
  */
  getVideoTypeAndId(url) {
    const regexMatch = url.match(
      /(http:|https:|)\/\/(player.|www.)?(y2u\.be|vimeo\.com|youtu(be\.com|\.be|be\.googleapis\.com))\/(video\/|embed\/|watch\?v=|v\/)?([A-Za-z0-9._%-]*)(&\S+)?/
    );
    let type = '';
    if (regexMatch && regexMatch.length > 5) {
      if (
        regexMatch[3].indexOf('youtu') > -1 ||
        regexMatch[3].indexOf('y2u') > -1
      ) {
        type = 'youtube';
      } else if (regexMatch[3].indexOf('vimeo') > -1) {
        type = 'vimeo';
      }
      return {
        type,
        videoId: regexMatch[6],
      };
    } else {
      return {
        type,
        videoId: url,
      };
    }
  },
  embedIframe(videoWrapper, videoUrl) {
    let videoEmbedUrl = '';
    const { type, videoId } = this.getVideoTypeAndId(videoUrl);
    if (type === 'youtube') {
      videoEmbedUrl = `<iframe src='//www.youtube.com/embed/${videoId}' frameborder='0' allowfullscreen></iframe>`;
    } else if (type === 'vimeo') {
      videoEmbedUrl = `<iframe src='https://player.vimeo.com/video/${videoId}' frameborder='0' allowfullscreen></iframe>`;
    }
    if (videoEmbedUrl) {
      videoWrapper.innerHTML = videoEmbedUrl;
    }
  },
};

export const TableSearch = function (tableId) {
  // a little library that takes a table id
  // and provides a method to search the table's rows for a given query.
  // the row's td must contain the class 'js-searchable' to be considered
  // for searching.
  // Eg:
  // var tableSearch = new TableSearch('tableId');
  // var hits = tableSearch.searchRows('someQuery');
  // 'hits' is a list of ids of the table's rows which contained 'someQuery'
  this.tableId = tableId;
  this.rowData = [];
  this.allMatchedIds = [];
};

TableSearch.prototype.getRows = function () {
  const tablerow = `#${this.tableId} tbody tr`;
  return $(tablerow);
};

TableSearch.prototype.setRowData = function () {
  // Builds a list of objects and sets it the object's rowData
  const rowMap = [];
  $.each(this.getRows(), (rowIndex, row) => {
    const rowid = $(row).attr('id');
    rowMap.push({
      rid: `#${rowid}`,
      text: $(row).find('td.js-searchable').text().toLowerCase(),
    });
  });
  this.rowData = rowMap;
};

TableSearch.prototype.setAllMatchedIds = function (ids) {
  this.allMatchedIds = ids;
};

TableSearch.prototype.searchRows = function (q) {
  // Search the rows of the table for a supplied query.
  // reset data collection on first search or if table has changed
  if (this.rowData.length !== this.getRows().length) {
    this.setRowData();
  } // return cached matched ids if query is blank

  if (q === '' && this.allMatchedIds.length !== 0) {
    return this.allMatchedIds;
  }

  const matchedIds = [];

  for (let i = this.rowData.length - 1; i >= 0; i -= 1) {
    if (this.rowData[i].text.indexOf(q.toLowerCase()) !== -1) {
      matchedIds.push(this.rowData[i].rid);
    }
  } // cache ids if query is blank

  if (q === '') {
    this.setAllMatchedIds(matchedIds);
  }

  return matchedIds;
};
