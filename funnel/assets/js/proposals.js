import { TableSearch } from './util';

$(() => {
  window.Hasgeek.ProposalsInit = function ({ search = '', sort = '' }) {
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
      $('.proposal-list-table tbody').sortable({
        placeholder: $(this).data('drag-placeholder'),
        cursor: 'move',
        update: function (event, ui) {
          var sortedIDs = $(this).sortable('toArray');
          var currentID = $(ui.item).attr('id');
          var currentIndex = sortedIDs.indexOf(currentID);
          $.ajax({
            url: sort.url,
            type: 'POST',
            data: {
              csrf_token: $('meta[name="csrf-token"]').attr('content'),
              currentItemId: currentID,
              previousItemId:
                currentID === 0 ? null : sortedIDs[currentIndex - 1],
            },
            dataType: 'json',
          });
        },
      });
    }
  };
});
