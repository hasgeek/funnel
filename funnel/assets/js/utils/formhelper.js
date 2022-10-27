const Form = {
  getElementId(htmlString) {
    return htmlString.match(/id="(.*?)"/)[1];
  },
  getErrorMsg(response, errorResponse = '') {
    let errorMsg = '';
    if (response.status === 500) {
      errorMsg = window.Hasgeek.Config.errorMsg.serverError;
    }
    if (
      response.status === 422 &&
      errorResponse &&
      errorResponse.error === 'requires_sudo'
    ) {
      window.location.assign(
        `${window.Hasgeek.Config.accountSudo}?next=${encodeURIComponent(
          window.location.href
        )}`
      );
    } else if (
      response.status === 422 &&
      errorResponse &&
      errorResponse.error === 'redirect'
    ) {
      window.location.assign(errorResponse.sudo_url);
    } else if (errorResponse && errorResponse.error_description) {
      errorMsg = errorResponse.error_description;
    } else {
      errorMsg = response.statusText;
    }
    return errorMsg;
  },
  getFetchError(response, xhr = true) {
    if (!xhr) {
      response.json().then((errorResponse) => {
        return Form.getErrorMsg(response, errorResponse);
      });
    }
    return this.getErrorMsg(response, response.responseJSON);
  },
  getResponseError(response) {
    let errorMsg = '';
    if (!Object.prototype.hasOwnProperty.call(response, 'readyState')) {
      errorMsg = this.getFetchError(response, false);
    } else if (response.readyState === 4) {
      errorMsg = this.getFetchError(response);
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
  handleFetchNetworkError() {
    const errorMsg = window.Hasgeek.Config.errorMsg.networkError;
    window.toastr.error(errorMsg);
    return errorMsg;
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
    $('body').on('click', elementClass, async function remove(event) {
      event.preventDefault();
      const url = $(this).attr('href');
      const confirmationText = window.gettext('Are you sure you want to remove %s?', [
        $(this).attr('title'),
      ]);

      /* eslint-disable no-alert */
      if (window.confirm(confirmationText)) {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            csrf_token: $('meta[name="csrf-token"]').attr('content'),
          }).toString(),
        }).catch(Form.handleFetchNetworkError);
        if (response && response.ok) {
          const responseData = await response.text();
          if (responseData) {
            onSucessFn(responseData);
          }
        } else {
          Form.handleAjaxError(response);
        }
      }
    });
  },
  activateToggleSwitch(callbckfn = '') {
    $('body').on('change', '.js-toggle', function submitToggleSwitch() {
      const checkbox = $(this);
      const currentState = this.checked;
      const previousState = !currentState;
      const formData = new FormData($(checkbox).parent('form')[0]);
      if (!currentState) {
        formData.append($(this).attr('name'), false);
      }

      fetch($(checkbox).parent('form').attr('action'), {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams(formData).toString(),
      })
        .then((responseData) => {
          if (responseData && responseData.message) {
            window.toastr.success(responseData.message);
          }
          if (callbckfn) {
            callbckfn();
          }
        })
        .catch((error) => {
          Form.handleAjaxError(error);
          $(checkbox).prop('checked', previousState);
        });
    });

    $('body').on('click', '.js-dropdown-toggle', function stopPropagation(event) {
      event.stopPropagation();
    });
  },
  openSubmissionToggle(checkboxId, cfpStatusDiv) {
    const onSuccess = () => {
      $(cfpStatusDiv).toggleClass('mui--hide');
    };
    Form.activateToggleSwitch(onSuccess);
  },
  handleCodemirrorFormSubmit(formId, view) {
    $(`#${formId}`).on('submit', () => {
      $(`#${formId}`).find('textarea').val(view.state.doc.toString());
    });
  },
};

export default Form;
