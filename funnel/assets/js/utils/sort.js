import Form from './formhelper';

function SortItem(wrapperJqueryElem, placeholderClass, sortUrl) {
  let oldList;
  let target;
  let other;
  let before;
  let newList;
  let newPosition;
  wrapperJqueryElem.sortable({
    handle: '.drag-handle',
    placeholder: placeholderClass,
    forcePlaceholderSize: true,
    revert: true,
    scroll: true,
    start(event, ui) {
      $(`.${placeholderClass}`).height($(ui.item).height());
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
        url: sortUrl,
        type: 'POST',
        data: {
          csrf_token: $('meta[name="csrf-token"]').attr('content'),
          target,
          other,
          before,
        },
        dataType: 'json',
        error(errorResponse) {
          Form.handleAjaxError(errorResponse);
          wrapperJqueryElem.sortable('cancel');
        },
      });
    },
  });
}

export default SortItem;
