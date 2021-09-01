import { Utils, TableSearch } from './util';

$(() => {
  window.Hasgeek.submissionsInit = function submissionsInit({
    search = '',
    sort = '',
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
      let oldList;
      let target;
      let other;
      let before;
      let newList;
      let newPosition;
      $('.proposal-list-table tbody').sortable({
        handle: '.drag-handle',
        placeholder: 'proposal-placeholder',
        forcePlaceholderSize: true,
        revert: true,
        scroll: true,
        start(event, ui) {
          $('.proposal-placeholder').height($(ui.item).height());
          oldList = $(this).sortable('toArray');
        },
        update(event, ui) {
          // True if moved up
          before = !(ui.position.top - ui.originalPosition.top > 0);
          newList = $(this).sortable('toArray');
          target = $(ui.item).attr('id');
          newPosition = newList.indexOf(target);
          other = oldList[newPosition];
          $.ajax({
            url: sort.url,
            type: 'POST',
            data: {
              csrf_token: $('meta[name="csrf-token"]').attr('content'),
              target,
              other,
              before,
            },
            dataType: 'json',
            error(errorResponse) {
              Utils.handleAjaxError(errorResponse);
              $('.proposal-list-table tbody').sortable('cancel');
            },
          });
        },
      });
    }
  };
});
