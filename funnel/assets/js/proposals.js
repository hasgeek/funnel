import { TableSearch } from './util';

$(() => {
  window.HasGeek.ProposalsInit = function ({ search = '' }) {
    if (search) {
      const tableSearch = new TableSearch(search.tableId);
      const inputId = `#${search.inputId}`;
      const tableRow = `#${search.tableId} tbody tr`;
      $(inputId).keyup(function keyup() {
        if ($('.collapsible__body').css('display') === 'none') {
          $('.collapsible__icon').toggleClass('mui--hide');
          $('.collapsible__body').slideToggle();
        }
        $(tableRow).addClass('mui--hide');
        const hits = tableSearch.searchRows($(this).val());
        $(hits.join(',')).removeClass('mui--hide');
      });
    }
  };
});
