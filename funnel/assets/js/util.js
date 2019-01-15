/* global ga */

export const Utils = {
  // convert array of objects into hashmap
  tohashMap(objectArray, key) {
    let hashMap = {
    };
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
    $('.collapsible__header').click(function collapseContent() {
      $(this).find('.collapsible__icon').toggleClass('mui--hide');
      $(this).next('.collapsible__body').slideToggle();
    });
  },
  animateScrollTo(offsetY) {
    $('html,body').animate({
      scrollTop: offsetY,
    }, 500);
  },
  smoothScroll() {
    $('a.smooth-scroll').on('click', function clickHandler(event) {
      event.preventDefault();
      Utils.animateScrollTo($(this.hash).offset().top);
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
  let tablerow = `#${this.tableId} tbody tr`;
  return $(tablerow);
};

TableSearch.prototype.setRowData = function () {
  // Builds a list of objects and sets it the object's rowData
  let rowMap = [];
  $.each(this.getRows(), (rowIndex, row) => {
    let rowid = $(row).attr('id');
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
  }
  // return cached matched ids if query is blank
  if (q === '' && this.allMatchedIds.length !== 0) {
    return this.allMatchedIds;
  }
  let matchedIds = [];
  for (let i = this.rowData.length - 1; i >= 0; i -= 1) {
    if (this.rowData[i].text.indexOf(q.toLowerCase()) !== -1) {
      matchedIds.push(this.rowData[i].rid);
    }
  }
  // cache ids if query is blank
  if (q === '') {
    this.setAllMatchedIds(matchedIds);
  }
  return matchedIds;
};
