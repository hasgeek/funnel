const Form = {
  getElementId(htmlString) {
    return htmlString.match(/id="(.*?)"/)[1];
  },
  getResponseError(response) {
    let errorMsg = '';
    if (response.readyState === 4) {
      if (response.status === 500) {
        errorMsg = window.Hasgeek.Config.errorMsg.serverError;
      } else if (
        response.status === 422 &&
        response.responseJSON.error === 'requires_sudo'
      ) {
        window.location.assign(
          `${window.Hasgeek.Config.accountSudo}?next=${encodeURIComponent(
            window.location.href
          )}`
        );
      } else if (
        response.status === 422 &&
        response.responseJSON.error === 'redirect'
      ) {
        window.location.assign(response.responseJSON.location);
      } else {
        errorMsg = response.responseJSON.error_description;
      }
    } else {
      errorMsg = window.Hasgeek.Config.errorMsg.networkError;
    }
    return errorMsg;
  },
  handleAjaxError(errorResponse) {
    Form.updateFormNonce(errorResponse.responseJSON);
    const errorMsg = Form.getResponseError(errorResponse);
    window.toastr.error(errorMsg);
    return errorMsg;
  },
  formErrorHandler(formId, errorResponse) {
    $(`#${formId}`).find('button[type="submit"]').attr('disabled', false);
    $(`#${formId}`).find('.loading').addClass('mui--hide');
    return Form.handleAjaxError(errorResponse);
  },
  getActionUrl(formId) {
    return $(`#${formId}`).attr('action');
  },
  updateFormNonce(response) {
    if (response && response.form_nonce) {
      $('input[name="form_nonce"]').val(response.form_nonce);
    }
  },
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
  },
  handleDelete(elementClass, onSucessFn) {
    $('body').on('click', elementClass, function remove(event) {
      event.preventDefault();
      const url = $(this).attr('href');
      const confirmationText = window.gettext(
        'Are you sure you want to remove %s?',
        [$(this).attr('title')]
      );

      /* eslint-disable no-alert */
      if (window.confirm(confirmationText)) {
        $.ajax({
          type: 'POST',
          url,
          data: {
            csrf_token: $('meta[name="csrf-token"]').attr('content'),
          },
          success(responseData) {
            onSucessFn(responseData);
          },
          error(response) {
            const errorMsg = Form.getResponseError(response);
            window.toastr.error(errorMsg);
          },
        });
      }
    });
  },
  activateToggleSwitch(callbckfn = '') {
    $('body').on('change', '.js-toggle', function submitToggleSwitch() {
      const checkbox = $(this);
      const currentState = this.checked;
      const previousState = !currentState;
      const formData = $(checkbox).parent('form').serializeArray();
      if (!currentState) {
        formData.push({ name: $(this).attr('name'), value: 'false' });
      }
      $.ajax({
        type: 'POST',
        url: $(checkbox).parent('form').attr('action'),
        data: formData,
        dataType: 'json',
        timeout: window.Hasgeek.Config.ajaxTimeout,
        success(responseData) {
          if (responseData && responseData.message) {
            window.toastr.success(responseData.message);
          }
          if (callbckfn) {
            callbckfn();
          }
        },
        error(response) {
          Form.handleAjaxError(response);
          $(checkbox).prop('checked', previousState);
        },
      });
    });

    $('body').on(
      'click',
      '.js-dropdown-toggle',
      function stopPropagation(event) {
        event.stopPropagation();
      }
    );
  },
  openSubmissionToggle(checkboxId, cfpStatusDiv) {
    const onSuccess = () => {
      $(cfpStatusDiv).toggleClass('mui--hide');
    };
    Form.activateToggleSwitch(onSuccess);
  },
};

export default Form;
