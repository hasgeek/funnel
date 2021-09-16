/* global gettext */
import Form from './formhelper';

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
    $('.collapsible__header').on('click', function collapseContent() {
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
      $('.header__nav-links--active').removeClass(
        'header__nav-links--menuOpen'
      );
    };

    const updatePageNumber = () => {
      page += 1;
    };

    const fetchMenu = (pageNo = 1) => {
      $.ajax({
        type: 'GET',
        url: `${url}?page=${pageNo}`,
        timeout: window.Hasgeek.Config.ajaxTimeout,
        success(responseData) {
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
        },
      });
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
      const firstActiveWeek = $(this).find(
        '.calendar__weekdays__dates--upcoming'
      ).length
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

      const todayDate = $(this)
        .find('.calendar__month__counting')
        .data('today');
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
      url: window.Hasgeek.Config.notificationCount,
      dataType: 'json',
      timeout: window.Hasgeek.Config.ajaxTimeout,
      success(responseData) {
        Utils.setNotifyIcon(responseData.unread);
      },
    });
  },
  addWebShare() {
    if (navigator.share) {
      $('.project-links').hide();
      $('.hg-link-btn').removeClass('mui--hide');

      $('body').on('click', '.hg-link-btn', function clickWebShare(event) {
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
      $('body').on('click', '.js-copy-link', function clickCopyLink(event) {
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
  activateToggleSwitch() {
    $('.js-toggle').on('change', function submitToggleSwitch() {
      const checkbox = $(this);
      const currentState = this.checked;
      const previousState = !currentState;
      const formData = $(checkbox).parent('form').serializeArray();
      if (!currentState) {
        formData.push({ name: $(this).attr('name'), value: 'false' });
      }
      $.ajax({
        type: 'POST',
        url: $(checkbox).parent('form').attr('action'),
        data: formData,
        dataType: 'json',
        timeout: window.Hasgeek.Config.ajaxTimeout,
        success(responseData) {
          if (responseData && responseData.message) {
            window.toastr.success(responseData.message);
          }
        },
        error(response) {
          Form.handleAjaxError(response);
          $(checkbox).prop('checked', previousState);
        },
      });
    });

    $('.js-dropdown-toggle').on('click', (event) => {
      event.stopPropagation();
    });
  },
};

export default Utils;
