import TableSearch from './utils/tablesearch';

$(() => {
  window.Hasgeek.profileFollowersInit = (search) => {
    if (search) {
      const tableSearch = new TableSearch(search.tableId);
      const inputId = `#${search.inputId}`;
      const tableRow = `#${search.tableId} tbody tr`;
      $(inputId).keyup(function doTableSearch() {
        $(tableRow).addClass('mui--hide');
        const hits = tableSearch.searchRows($(this).val());
        $(hits.join(',')).removeClass('mui--hide');
      });
    }
  };
});
