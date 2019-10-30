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
    $('a.js-smooth-scroll').on('click', function clickHandler(event) {
      event.preventDefault();
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
        !$.contains(
          $('.js-search-show').parent('.header__nav-list__item')[0],
          event.target
        )
      ) {
        $('.js-search-form').removeClass('search-form--show');
      }
    });
  },

  sendToGA(category, action, label, value = '') {
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
  const onSuccess = function() {
    $(`#${formId}`)
      .find('button')
      .css('display', 'inline-block')
      .prop('disabled', false)
      .toggleClass('mui--hide');
  };

  const onError = function(response) {
    let errorMsg = '';

    if (response.readyState === 4) {
      if (response.status === 500) {
        errorMsg = 'Internal Server Error. Please reload and try again.';
      } else {
        errorMsg = JSON.parse(response.responseText).error_description;
      }
    } else {
      errorMsg = 'Unable to connect. Please reload and try again.';
    }

    window.toastr.error(errorMsg);
  };

  window.Baseframe.Forms.handleFormSubmit(
    formId,
    postUrl,
    onSuccess,
    onError,
    config
  );
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
