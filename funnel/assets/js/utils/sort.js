import 'jquery-ui';
import 'jquery-ui-sortable-npm';
import 'jquery-ui-touch-punch';
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
    async update(event, ui) {
      // True if moved up
      before = !(ui.position.top - ui.originalPosition.top > 0);
      newList = $(this).sortable('toArray');
      target = $(ui.item).attr('id');
      newPosition = newList.indexOf(target);
      other = oldList[newPosition];

      function handleError(error) {
        if (!error.response) {
          Form.handleFetchNetworkError();
        } else {
          Form.handleAjaxError(error);
        }
        wrapperJqueryElem.sortable('cancel');
      }

      const response = await fetch(sortUrl, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          csrf_token: $('meta[name="csrf-token"]').attr('content'),
          target,
          other,
          before,
        }).toString(),
      }).catch(handleError);
      if (!response.ok) {
        handleError(response);
      }
    },
  });
}

export default SortItem;
