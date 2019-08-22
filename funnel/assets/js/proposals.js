import { SaveProject, TableSearch } from './util';

$(() => {
  window.HasGeek.ProposalsInit = function ({search='', saveProjectConfig=''}) {

    if (search) {
      let tableSearch = new TableSearch(search.tableId);
      let inputId = `#${search.inputId}`;
      let tableRow = `#${search.tableId} tbody tr`;
      $(inputId).keyup(function keyup() {
        if ($('.collapsible__body').css('display') === 'none') {
          $('.collapsible__icon').toggleClass('mui--hide');
          $('.collapsible__body').slideToggle();
        }
        $(tableRow).addClass('mui--hide');
        let hits = tableSearch.searchRows($(this).val());
        $(hits.join(',')).removeClass('mui--hide');
      });
    }

    if (saveProjectConfig) {
      SaveProject(saveProjectConfig);
    }
  };
});
