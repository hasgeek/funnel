import TableSearch from './utils/tablesearch';
import sortItem from './utils/sort';
import { Widgets } from './utils/form_widgets';

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
      sortItem($(sort.wrapperElem), sort.placeholder, sort.url);
    }

    if (openSubmission) {
      Widgets.openSubmissionToggle(
        openSubmission.toggleId,
        openSubmission.cfpStatusElem,
      );
    }
  };
});
