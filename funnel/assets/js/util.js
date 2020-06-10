/* global ga */
export const Utils = {
  // convert array of objects into hashmap
  tohashMap(objectArray, key) {
    const hashMap = {};
    objectArray.forEach(obj => {
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
      $(this)
        .find('.collapsible__icon')
        .toggleClass('mui--hide');
      $(this)
        .siblings('.collapsible__body')
        .slideToggle();
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
      $('#jquery-scroll-tabs .js-scroll-prev').on('click', event => {
        event.preventDefault();
        const prevTab = $('.tabs__item--active')
          .prev('.tabs__item')
          .attr('href');

        if (prevTab) {
          window.location.href = prevTab;
        }
      });
      $('#jquery-scroll-tabs .js-scroll-next').on('click', event => {
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
    $('.js-truncate').each(function() {
      let linesLimit = $(this).data('truncate-lines');
      $(this).trunk8({
        lines: linesLimit,
      });
    });

    $('.js-truncate-readmore').each(function() {
      let linesLimit = $(this).data('truncate-lines');
      $(this).trunk8({
        lines: linesLimit,
        fill:
          '&hellip;<span class="js-read-more mui--text-hyperlink read-more">read more</span>',
      });
    });

    $('.js-read-more').click(function() {
      $(this)
        .parent('.js-truncate-readmore')
        .trunk8('revert');
    });
  },
  showTimeOnCalendar() {
    let firstActiveWeek = $('body .calendar__weekdays').find(
      '.calendar__weekdays__dates--upcoming:first'
    ).length
      ? $('body .calendar__weekdays').find(
          '.calendar__weekdays__dates--upcoming:first'
        )
      : $('body .calendar__weekdays').find('.calendar__weekdays__dates:first');

    firstActiveWeek
      .find('.calendar__weekdays__dates__date--showtime:first')
      .addClass('calendar__weekdays__dates__date--display');

    $('body .calendar__weekdays__dates__date--showtime').hover(function() {
      $(this)
        .parents('.calendar__weekdays')
        .find('.calendar__weekdays__dates__date--showtime')
        .removeClass('calendar__weekdays__dates__date--display');
    });

    $('body .calendar__weekdays__dates__date--showtime').mouseleave(function() {
      firstActiveWeek
        .find('.calendar__weekdays__dates__date--showtime:first')
        .addClass('calendar__weekdays__dates__date--display');
    });

    const singleDay = 24 * 60 * 60 * 1000;

    $('body .card__calendar').each(function() {
      let todayDate = $(this)
        .find('.calendar__counting')
        .data('today');
      let nextEventElem = $(this)
        .find('.calendar__weekdays__dates--upcoming--first')
        .first()
        .find('.calendar__weekdays__dates__date--active')
        .first();
      let eventDate = nextEventElem.data('event-date');
      let eventMonth = nextEventElem.data('event-month');
      let monthElem = $(this)
        .find('.calendar__month-name')
        .find("[data-month='" + eventMonth + "']");

      // Today's date in terms of number of milliseconds since January 1, 1970, 00:00:00 UTC
      let today = Date.parse(todayDate);
      // Event date in terms of number of milliseconds since January 1, 1970, 00:00:00 UTC
      let eventDay = Date.parse(eventDate);
      // Find the difference between event and today's date in UTC
      let counting = Math.round((eventDay - today) / singleDay);
      let dayText = ['Today', 'Tomorrow', 'Day after'];
      // Show number of days on the widget only if it is less than 32 days
      if (counting >= 0 && counting < 3) {
        monthElem.text(dayText[counting]);
      } else if (counting > 2 && counting < 32) {
        let daysRemainingTxt = `In ${counting} days`;
        monthElem.text(daysRemainingTxt);
      }
    });
  },
  getElementId(htmlString) {
    return htmlString.match(/id="(.*?)"/)[1];
  },
  getResponseError(response) {
    let errorMsg = '';

    if (response.readyState === 4) {
      if (response.status === 500) {
        errorMsg =
          'An internal server error occurred. Our support team has been notified and will investigate.';
      } else {
        errorMsg = JSON.parse(response.responseText).error_description;
      }
    } else {
      errorMsg = 'Unable to connect. Please reload and try again.';
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
    $(`#${formId}`)
      .find('button[type="submit"]')
      .prop('disabled', false);
    $(`#${formId}`)
      .find('.loading')
      .addClass('mui--hide');
    return Utils.handleAjaxError(errorResponse);
  },
  getActionUrl(formId) {
    return $(`#${formId}`).attr('action');
  },
  updateFormNonce(response) {
    if (response.form_nonce) {
      $('input[name="form_nonce"]').val(response.form_nonce);
    }
  },
  popupBackHandler() {
    $('.js-popup-back').on('click', function(event) {
      if (document.referrer !== '') {
        event.preventDefault();
        window.history.back();
      }
    });
  },
};

export const ScrollActiveMenu = {
  init(navId, navItemsClassName, activeMenuClassName) {
    this.navId = navId;
    this.navItemsClassName = navItemsClassName;
    this.activeMenuClassName = activeMenuClassName;
    this.navItems = [...document.querySelectorAll(`.${navItemsClassName}`)];
    this.headings = this.navItems.map(navItem => {
      if (navItem.classList.contains('js-samepage')) {
        return document.querySelector(navItem.getAttribute('href'));
      }

      return false;
    });
    this.handleObserver = this.handleObserver.bind(this);
    this.headings.forEach(heading => {
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

    if (document.getElementById('ticket-wrapper')) {
      const observer = new IntersectionObserver(
        entries => {
          entries.forEach(entry => {
            if (
              !entry.isIntersecting &&
              entry.intersectionRatio > 0.5 &&
              entry.boundingClientRect.y < 0
            ) {
              $('#ticket-btn').addClass('sub-navbar__item--fixed');
            } else if (entry.isIntersecting && entry.intersectionRatio === 1) {
              $('#ticket-btn').removeClass('sub-navbar__item--fixed');
            }
          });
        },
        {
          rootMargin: '0px',
          threshold: 1,
        }
      );
      observer.observe(document.getElementById('ticket-wrapper'));
    }
  },

  handleObserver(entries) {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const activeNavItem = this.navItems.find(
          navItem =>
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
    this.imgItems.forEach(img => {
      if (img) {
        let observer = new IntersectionObserver(
          entries => {
            entries.forEach(entry => {
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
export const SaveProject = function({ formId, postUrl, config = {} }) {
  const onSuccess = function(response) {
    $(`#${formId}`)
      .find('button')
      .prop('disabled', false)
      .removeClass('animate-btn--animate');

    $(`#${formId}`)
      .find('button')
      .each(function() {
        if ($(this).hasClass('animate-btn--show')) {
          $(this).removeClass('animate-btn--show');
        } else {
          $(this).addClass('animate-btn--show');
          if ($(this).hasClass('animate-btn--saved')) {
            $(this).addClass('animate-btn--animate');
            window.toastr.success('Project added to Account > My saves');
          }
        }
      });
    Utils.updateFormNonce(response);
  };

  const onError = function(response) {
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

export const TableSearch = function(tableId) {
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

TableSearch.prototype.getRows = function() {
  const tablerow = `#${this.tableId} tbody tr`;
  return $(tablerow);
};

TableSearch.prototype.setRowData = function() {
  // Builds a list of objects and sets it the object's rowData
  const rowMap = [];
  $.each(this.getRows(), (rowIndex, row) => {
    const rowid = $(row).attr('id');
    rowMap.push({
      rid: `#${rowid}`,
      text: $(row)
        .find('td.js-searchable')
        .text()
        .toLowerCase(),
    });
  });
  this.rowData = rowMap;
};

TableSearch.prototype.setAllMatchedIds = function(ids) {
  this.allMatchedIds = ids;
};

TableSearch.prototype.searchRows = function(q) {
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

export const Comments = {
  init() {
    const newCommentUrl = $('#comment-form').attr('action');

    $('.comment .js-collapse').click(function() {
      $(this).addClass('mui--hide');
      $(this)
        .siblings('.js-uncollapse')
        .removeClass('mui--hide');
      $(this)
        .parent()
        .siblings('.comment--body')
        .slideUp('fast');
      $(this)
        .parent()
        .siblings('.comment--children')
        .slideUp('fast');
      return false;
    });

    $('.comment .js-uncollapse').click(function() {
      $(this).addClass('mui--hide');
      $(this)
        .siblings('.js-collapse')
        .removeClass('mui--hide');
      $(this)
        .parent()
        .siblings('.comment--body')
        .slideDown('fast');
      $(this)
        .parent()
        .siblings('.comment--children')
        .slideDown('fast');
      return false;
    });

    $('.comment .js-comment-reply').click(function() {
      const cfooter = $(this).parent();
      $('#comment-form input[name="parent_id"]').val(cfooter.attr('data-id'));
      $('#comment-form  input[name="comment_edit_id"]').val('');
      $('#toplevel-comment, #comment-cancel').removeClass('mui--hide');
      $('#comment-submit').val('Reply'); // i18n gotcha
      cfooter.after($('#comment-form'));
      $('#comment-form textarea').focus();
      return false;
    });

    $('#toplevel-comment a, #comment-cancel').click(function() {
      $('#comment-form').attr('action', newCommentUrl);
      $('#comment-form  input[name="parent_id"]').val('');
      $('#comment-form  input[name="comment_edit_id"]').val('');
      $('#comment-submit').val('Post comment'); // i18n gotcha
      $('#comment-form .message .CodeMirror')[0].CodeMirror.setValue('');
      $('#toplevel-comment a')
        .parent()
        .after($('#comment-form'));
      $('#toplevel-comment a')
        .parent()
        .addClass('mui--hide');
      $('#toplevel-comment, #comment-cancel').addClass('mui--hide');
      $('#comment-form textarea').focus();
      return false;
    });

    $('.comment .js-comment-delete').click(function() {
      const cfooter = $(this).parent();
      $('#delcomment input[name="comment_id"]').val(cfooter.attr('data-id'));
      $('#delcomment').attr('action', cfooter.attr('data-delete-url'));
      $('#delcomment')
        .removeClass('mui--hide')
        .hide()
        .insertAfter(cfooter)
        .slideDown('fast');
      return false;
    });

    $('#comment-delete-cancel').click(() => {
      $('#delcomment').slideUp('fast');
      return false;
    });

    $('.comment .js-comment-edit').click(function() {
      const cfooter = $(this).parent();
      const cid = cfooter.attr('data-id');
      const editUrl = cfooter.attr('data-json-url');
      $(cfooter)
        .find('.loading')
        .removeClass('mui--hide');
      $('#comment-form').attr('action', cfooter.attr('data-edit-url'));
      $.getJSON(editUrl, data => {
        $('#comment-form .message .CodeMirror')[0].CodeMirror.setValue(
          data.message
        );
      });
      $('#comment-form input[name="parent_id"]').val('');
      $('#comment-form input[name="comment_edit_id"]').val(cid);
      $('#toplevel-comment').removeClass('mui--hide');
      $(cfooter)
        .find('.loading')
        .addClass('mui--hide');
      $('#comment-submit').val('Save changes');
      cfooter.after($('#comment-form'));
      $('#comment-form textarea').focus();
      return false;
    });
  },
};
