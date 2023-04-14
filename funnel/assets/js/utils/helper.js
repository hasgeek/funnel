/* global gettext */
const Utils = {
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
    $('body').on('click', '.collapsible__header', function collapseContent() {
      $(this).find('.collapsible__icon').toggleClass('mui--hide');
      $(this).siblings('.collapsible__body').slideToggle();
    });
  },
  popupBackHandler() {
    $('.js-popup-back').on('click', (event) => {
      if (document.referrer !== '') {
        event.preventDefault();
        window.history.back();
      }
    });
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
    const menuBtn = $(menuBtnClass);
    const topMargin = 1;
    const headerHeight = $('.header').height() + topMargin;
    let page = 1;
    let lazyLoader;
    let observer;

    const openMenu = () => {
      if ($(window).width() < window.Hasgeek.Config.mobileBreakpoint) {
        $(menuWrapper).find(menu).animate({ top: '0' });
      } else {
        $(menuWrapper).find(menu).animate({ top: headerHeight });
      }
      $('.header__nav-links--active').addClass('header__nav-links--menuOpen');
      menuBtn.addClass('header__nav-links--active');
      $('body').addClass('body-scroll-lock');
    };

    const closeMenu = () => {
      if ($(window).width() < window.Hasgeek.Config.mobileBreakpoint) {
        $(menuWrapper).find(menu).animate({ top: '100vh' });
      } else {
        $(menuWrapper).find(menu).animate({ top: '-100vh' });
      }
      menuBtn.removeClass('header__nav-links--active');
      $('body').removeClass('body-scroll-lock');
      $('.header__nav-links--active').removeClass('header__nav-links--menuOpen');
    };

    const updatePageNumber = () => {
      page += 1;
    };

    const fetchMenu = async (pageNo = 1) => {
      const menuUrl = `${url}?${new URLSearchParams({
        page: pageNo,
      }).toString()}`;
      const response = await fetch(menuUrl, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      if (response && response.ok) {
        const responseData = await response.text();
        if (responseData) {
          if (observer) {
            observer.unobserve(lazyLoader);
            $('.js-load-comments').remove();
          }
          $(menuWrapper).find(menu).append(responseData);
          updatePageNumber();
          lazyLoader = document.querySelector('.js-load-comments');
          if (lazyLoader) {
            observer = new IntersectionObserver(
              (entries) => {
                entries.forEach((entry) => {
                  if (entry.isIntersecting) {
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
        }
      }
    };

    // If user logged in, preload menu
    if ($(menuWrapper).length) {
      fetchMenu();
    }

    // Open full screen account menu in mobile
    menuBtn.on('click', function clickOpenCloseMenu() {
      if ($(this).hasClass('header__nav-links--active')) {
        closeMenu();
      } else {
        openMenu();
      }
    });

    $('body').on('click', (event) => {
      const totalBtn = $(menuBtn).toArray();
      let isChildElem = false;
      totalBtn.forEach((element) => {
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
  truncate() {
    const readMoreTxt = `&hellip;<span class="js-read-more mui--text-hyperlink read-more">${gettext(
      'read more'
    )}</span>`;

    $('.js-truncate').each(function truncateLines() {
      const linesLimit = $(this).data('truncate-lines');
      $(this).trunk8({
        lines: linesLimit,
      });
    });

    $('.js-truncate-readmore').each(function truncateLinesReadMore() {
      const linesLimit = $(this).data('truncate-lines');
      $(this).trunk8({
        lines: linesLimit,
        fill: readMoreTxt,
        parseHTML: true,
      });
    });

    $('body').on('click', '.js-read-more', function clickReadMore() {
      $(this).parent('.js-truncate-readmore').trunk8('revert');
    });
  },
  showTimeOnCalendar() {
    const singleDay = 24 * 60 * 60 * 1000;

    $('body .card__calendar').each(function setupCardCalendar() {
      const firstActiveWeek = $(this).find('.calendar__weekdays__dates--upcoming')
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
        .hover(function hoverCardDate() {
          $(this)
            .parents('.calendar__weekdays')
            .find('.calendar__weekdays__dates__date--showtime')
            .removeClass('calendar__weekdays__dates__date--display');
        });

      $(this)
        .find('.calendar__weekdays__dates__date--showtime')
        .mouseleave(() => {
          firstActiveWeek
            .find(
              '.calendar__weekdays__dates__date--showtime.calendar__weekdays__dates__date--latest:first'
            )
            .addClass('calendar__weekdays__dates__date--display');
        });

      const todayDate = $(this).find('.calendar__month__counting').data('today');
      const nextEventElem = $(this)
        .find('.calendar__weekdays__dates--upcoming--first')
        .first()
        .find(
          '.calendar__weekdays__dates__date--showtime.calendar__weekdays__dates__date--latest'
        )
        .first();
      const eventDate = nextEventElem.data('event-date');
      const eventMonth = nextEventElem.data('event-month');
      const monthElem = $(this)
        .find('.calendar__month')
        .find(`[data-month='${eventMonth}']`);

      // Today's date in terms of number of milliseconds since January 1, 1970, 00:00:00 UTC
      const today = Date.parse(todayDate);
      // Event date in terms of number of milliseconds since January 1, 1970, 00:00:00 UTC
      const eventDay = Date.parse(eventDate);
      // Find the difference between event and today's date in UTC
      const counting = Math.round((eventDay - today) / singleDay);
      // Defined these strings in project_countdown macro in calendar_snippet.js.jinja2
      const dayText = [
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
  setNotifyIcon(unread) {
    if (unread) {
      $('.header__nav-links--updates').addClass('header__nav-links--updates--unread');
    } else {
      $('.header__nav-links--updates').removeClass(
        'header__nav-links--updates--unread'
      );
    }
  },
  async updateNotificationStatus() {
    const response = await fetch(window.Hasgeek.Config.notificationCount, {
      headers: {
        Accept: 'application/x.html+json',
        'X-Requested-With': 'XMLHttpRequest',
      },
    });
    if (response && response.ok) {
      const responseData = await response.json();
      Utils.setNotifyIcon(responseData.unread);
    }
  },
  async sendNotificationReadStatus() {
    const notificationID = this.getQueryString('utm_source');
    const Base58regex = /[\d\w]{21,22}/;

    if (notificationID && Base58regex.test(notificationID)) {
      const url = window.Hasgeek.Config.markNotificationReadUrl.replace(
        'eventid_b58',
        notificationID
      );
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          csrf_token: $('meta[name="csrf-token"]').attr('content'),
        }).toString(),
      });
      if (response && response.ok) {
        const responseData = await response.json();
        if (responseData) {
          Utils.setNotifyIcon(responseData.unread);
        }
      }
    }
  },
  addWebShare() {
    const utils = this;
    if (navigator.share) {
      $('.project-links').hide();
      $('.hg-link-btn').removeClass('mui--hide');

      const mobileShare = (title, url, text) => {
        navigator.share({
          title,
          url,
          text,
        });
      };

      $('body').on('click', '.hg-link-btn', function clickWebShare(event) {
        event.preventDefault();
        const linkElem = this;
        let url =
          $(linkElem).data('url') ||
          (document.querySelector('link[rel=canonical]') &&
            document.querySelector('link[rel=canonical]').href) ||
          window.location.href;
        const title = $(this).data('title') || document.title;
        const text = $(this).data('text') || '';
        if ($(linkElem).attr('data-shortlink')) {
          mobileShare(title, url, text);
        } else {
          utils
            .fetchShortUrl(url)
            .then((shortlink) => {
              url = shortlink;
              $(linkElem).attr('data-shortlink', true);
            })
            .finally(() => {
              mobileShare(title, url, text);
            });
        }
      });
    } else {
      $('body').on('click', '.js-copy-link', function clickCopyLink(event) {
        event.preventDefault();
        const linkElem = this;
        const copyLink = () => {
          const url = $(linkElem).find('.js-copy-url').first().text();
          if (navigator.clipboard) {
            navigator.clipboard.writeText(url).then(
              () => window.toastr.success(gettext('Link copied')),
              () => window.toastr.success(gettext('Could not copy link'))
            );
          } else {
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents($(linkElem).find('.js-copy-url')[0]);
            selection.removeAllRanges();
            selection.addRange(range);
            if (document.execCommand('copy')) {
              window.toastr.success(gettext('Link copied'));
            } else {
              window.toastr.success(gettext('Could not copy link'));
            }
            selection.removeAllRanges();
          }
        };
        if ($(linkElem).attr('data-shortlink')) {
          copyLink();
        } else {
          utils
            .fetchShortUrl($(linkElem).find('.js-copy-url').first().html())
            .then((shortlink) => {
              $(linkElem).find('.js-copy-url').text(shortlink);
              $(linkElem).attr('data-shortlink', true);
            })
            .finally(() => {
              copyLink();
            });
        }
      });
    }
  },
  enableWebShare() {
    if (navigator.share) {
      $('.project-links').hide();
      $('.hg-link-btn').removeClass('mui--hide');
    }
  },
  async fetchShortUrl(url) {
    const response = await fetch(window.Hasgeek.Config.shorturlApi, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `url=${encodeURIComponent(url)}`,
    });
    if (response.ok) {
      const json = await response.json();
      return json.shortlink;
    }
    // Call failed, return the original URL
    return url;
  },
  getQueryString(paramName) {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has(paramName)) {
      return urlParams.get(paramName);
    }
    return false;
  },
  getInitials(name) {
    if (name) {
      const parts = name.split(/\s+/);
      const len = parts.length;
      if (len > 1) {
        return (
          (parts[0] ? parts[0][0] : '') + (parts[len - 1] ? parts[len - 1][0] : '')
        );
      }
      if (parts) {
        return parts[0] ? parts[0][0] : '';
      }
    }
    return '';
  },
  getAvatarColour(name) {
    const avatarColorCount = 6;
    const initials = this.getInitials(name);
    let stringTotal = 0;
    if (initials.length) {
      stringTotal = initials.charCodeAt(0);
      if (initials.length > 1) {
        stringTotal += initials.charCodeAt(1);
      }
    }
    return stringTotal % avatarColorCount;
  },
  activateZoomPopup() {
    if ($('.markdown').length > 0) {
      $('abbr').each(function () {
        if ($(this).offset().left > $(window).width() * 0.7) {
          $(this).addClass('tooltip-right');
        }
      });
    }

    $('body').on('click', '.markdown table, .markdown img', function (event) {
      event.preventDefault();
      $('body').append('<div class="markdown-modal markdown"></div>');
      $('.markdown-modal').html($(this)[0].outerHTML);
      $('.markdown-modal').modal();
    });

    $('body').on('click', '.markdown table a', (event) => {
      event.stopPropagation();
    });

    $('body').on($.modal.AFTER_CLOSE, '.markdown-modal', (event) => {
      event.preventDefault();
      $('.markdown-modal').remove();
    });
  },
  addFocusOnModalShow() {
    let focussedElem;
    $('body').on($.modal.OPEN, '.modal', function () {
      focussedElem = document.activeElement;
      Utils.trapFocusWithinModal(this);
    });

    $('body').on($.modal.CLOSE, '.modal', () => {
      focussedElem.focus();
    });
  },
  trapFocusWithinModal(modal) {
    const $this = $(modal);
    const focusableElems =
      'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, object, embed, *[tabindex], *[contenteditable]';
    const children = $this.find('*');
    const focusableItems = children.filter(focusableElems).filter(':visible');
    const numberOfFocusableItems = focusableItems.length;
    let focusedItem;
    let focusedItemIndex;
    $this.find('.modal__close').focus();

    $this.on('keydown', (event) => {
      if (event.keyCode !== 9) return;
      focusedItem = $(document.activeElement);
      focusedItemIndex = focusableItems.index(focusedItem);
      if (!event.shiftKey && focusedItemIndex === numberOfFocusableItems - 1) {
        focusableItems.get(0).focus();
        event.preventDefault();
      }
      if (event.shiftKey && focusedItemIndex === 0) {
        focusableItems.get(numberOfFocusableItems - 1).focus();
        event.preventDefault();
      }
    });
  },
  getFaiconHTML(icon, iconSize = 'body', baseline = true, cssClassArray = []) {
    const svgElem = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    const useElem = document.createElementNS('http://www.w3.org/2000/svg', 'use');

    svgElem.setAttribute('aria-hidden', true);
    svgElem.setAttribute('role', 'img');
    useElem.setAttributeNS(
      'http://www.w3.org/1999/xlink',
      'xlink:href',
      `${window.Hasgeek.Config.svgIconUrl}#${icon}`
    );
    svgElem.appendChild(useElem);
    svgElem.classList.add(`fa5-icon--${iconSize}`);
    if (baseline) {
      svgElem.classList.add('fa5--align-baseline');
    }
    svgElem.classList.add('fa5-icon', ...cssClassArray);
    return svgElem;
  },
  debounce(fn, timeout, context, ...args) {
    let timer = null;
    function debounceFn() {
      if (timer) clearTimeout(timer);
      const fnContext = context || this;
      timer = setTimeout(fn.bind(fnContext, ...args), timeout);
    }
    return debounceFn;
  },
};

export default Utils;
