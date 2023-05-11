const Modal = {
  handleModalForm() {
    $('.js-modal-form').click(function addModalToWindowHash() {
      window.location.hash = $(this).data('hash');
    });

    $('body').on($.modal.BEFORE_CLOSE, () => {
      if (window.location.hash) {
        window.history.replaceState(
          '',
          '',
          window.location.pathname + window.location.search
        );
      }
    });

    window.addEventListener(
      'hashchange',
      () => {
        if (window.location.hash === '') {
          $.modal.close();
        }
      },
      false
    );

    const hashId = window.location.hash.split('#')[1];
    if (hashId) {
      if ($(`a.js-modal-form[data-hash="${hashId}"]`).length) {
        $(`a[data-hash="${hashId}"]`).click();
      }
    }

    $('body').on('click', '.alert__close', function closeModal() {
      $(this).parents('.alert').fadeOut();
    });
  },
  trapFocusWithinModal(modal) {
    const $this = $(modal);
    const focusableElems =
      'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, object, embed, *[tabindex], *[contenteditable]';
    const children = $this.find('*');
    const focusableItems = children.filter(focusableElems).filter(':visible');
    const numberOfFocusableItems = focusableItems.length;
    let focusedItem;
    let focusedItemIndex;
    $this.find('.modal__close').focus();

    $this.on('keydown', (event) => {
      if (event.keyCode !== 9) return;
      focusedItem = $(document.activeElement);
      focusedItemIndex = focusableItems.index(focusedItem);
      if (!event.shiftKey && focusedItemIndex === numberOfFocusableItems - 1) {
        focusableItems.get(0).focus();
        event.preventDefault();
      }
      if (event.shiftKey && focusedItemIndex === 0) {
        focusableItems.get(numberOfFocusableItems - 1).focus();
        event.preventDefault();
      }
    });
  },
  addFocusOnModalShow() {
    let focussedElem;
    $('body').on($.modal.OPEN, '.modal', function moveFocusToModal() {
      focussedElem = document.activeElement;
      Modal.trapFocusWithinModal(this);
    });

    $('body').on($.modal.CLOSE, '.modal', () => {
      focussedElem.focus();
    });
  },
  activateZoomPopup() {
    if ($('.markdown').length > 0) {
      $('abbr').each(function alignToolTip() {
        if ($(this).offset().left > $(window).width() * 0.7) {
          $(this).addClass('tooltip-right');
        }
      });
    }

    $('body').on(
      'click',
      '.markdown table, .markdown img',
      function openTableInModal(event) {
        event.preventDefault();
        $('body').append('<div class="markdown-modal markdown"></div>');
        $('.markdown-modal').html($(this)[0].outerHTML);
        $('.markdown-modal').modal();
      }
    );

    $('body').on('click', '.markdown table a', (event) => {
      event.stopPropagation();
    });

    $('body').on($.modal.AFTER_CLOSE, '.markdown-modal', (event) => {
      event.preventDefault();
      $('.markdown-modal').remove();
    });
  },
  popupBackHandler() {
    $('.js-popup-back').on('click', (event) => {
      if (document.referrer !== '') {
        event.preventDefault();
        window.history.back();
      }
    });
  },
  addUsability() {
    this.handleModalForm();
    this.activateZoomPopup();
    this.addFocusOnModalShow();
    this.popupBackHandler();
  },
};

export default Modal;
