import { TableSearch } from './util';

$(() => {
  window.HasGeek.ProposalsInit = function ({search=''}) {

    if (search) {
      let tableSearch = new TableSearch(search.tableId);
      let inputId = `#${search.inputId}`;
      let tableRow = `#${search.tableId} tbody tr`;
      $(inputId).keyup(function keyup() {
        if ($('.collapsible__body').css('display') === 'none') {
          $('.collapsible__header').click();
        }
        $(tableRow).addClass('mui--hide');
        let hits = tableSearch.searchRows($(this).val());
        $(hits.join(',')).removeClass('mui--hide');
      });
    }
  };
});
