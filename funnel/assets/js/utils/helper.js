/* global gettext */
import toastr from 'toastr';

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
  async fetchShortUrl(url) {
    const response = await fetch(window.Hasgeek.Config.shorturlApi, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `url=${encodeURIComponent(url)}`,
    }).catch(() => {
      throw new Error(window.Hasgeek.Config.errorMsg.serverError);
    });
    if (response.ok) {
      const json = await response.json();
      return json.shortlink;
    }
    return Promise.reject(window.gettext('This URL is not valid for a shortlink'));
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
  csrfRefresh() {
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
  },
  copyToClipboard(elem) {
    const textElem = document.querySelector(elem);
    const stringToCopy = textElem.innerHTML;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(stringToCopy).then(
        () => toastr.success(window.gettext('Link copied')),
        () => toastr.success(window.gettext('Could not copy link'))
      );
    } else {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(textElem);
      selection.removeAllRanges();
      selection.addRange(range);
      if (document.execCommand('copy')) {
        toastr.success(window.gettext('Link copied'));
      } else {
        toastr.error(window.gettext('Could not copy link'));
      }
      selection.removeAllRanges();
    }
  },
};

export default Utils;
