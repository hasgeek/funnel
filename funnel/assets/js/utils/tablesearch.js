class TableSearch {
  constructor(tableId) {
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
  }

  getRows() {
    const tablerow = `#${this.tableId} tbody tr`;
    return $(tablerow);
  }

  setRowData() {
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
  }

  setAllMatchedIds(ids) {
    this.allMatchedIds = ids;
  }

  searchRows(q) {
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
  }
}

export default TableSearch;
