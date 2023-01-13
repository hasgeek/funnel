import TableSearch from './utils/tablesearch';
import SortItem from './utils/sort';
import Form from './utils/formhelper';

$(() => {
  window.Hasgeek.submissionsInit = function submissionsInit({
    search = '',
    sort = '',
    openSubmission = '',
  }) {
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

    if (sort.permission) {
      SortItem($('.proposal-list-table tbody'), 'proposal-placeholder', sort.url);
    }

    Form.openSubmissionToggle(openSubmission.toggleId, openSubmission.cfpStatusElem);
  };
});
