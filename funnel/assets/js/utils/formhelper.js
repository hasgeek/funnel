import toastr from 'toastr';

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
    toastr.error(errorMsg);
    return errorMsg;
  },
  formErrorHandler(formId, errorResponse) {
    $(`#${formId}`).find('button[type="submit"]').attr('disabled', false);
    $(`#${formId}`).find('.loading').addClass('mui--hide');
    return Form.handleAjaxError(errorResponse);
  },
  handleFetchNetworkError() {
    const errorMsg = window.Hasgeek.Config.errorMsg.networkError;
    toastr.error(errorMsg);
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
      const url = $(this).attr('data-href');
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
          const responseData = await response.json();
          if (responseData) {
            onSucessFn(responseData);
          }
        } else {
          Form.handleAjaxError(response);
        }
      }
    });
  },
  preventSubmitOnEnter(id) {
    $(`#${id}`).on('keyup keypress', (e) => {
      const code = e.keyCode || e.which;
      if (code === 13) {
        e.preventDefault();
        return false;
      }
      return true;
    });
  },
  preventDoubleSubmit(formId) {
    const form = $(`#${formId}`);
    form
      .find('input[type="submit"]')
      .prop('disabled', true)
      .addClass('submit-disabled');
    form
      .find('button[type="submit"]')
      .prop('disabled', true)
      .addClass('submit-disabled');
    form.find('.loading').removeClass('mui--hide');
  },
  /* Takes 'formId' and 'errors'
     'formId' is the id attribute of the form for which errors needs to be displayed
     'errors' is the WTForm validation errors expected in the following format
      {
        "title": [
          "This field is required"
        ]
        "email": [
          "Not a valid email"
        ]
      }
    For each error, a 'p' tag is created if not present and
    assigned the error value as its text content.
    The field wrapper and field are queried in the DOM
    using the unique form id. And the newly created 'p' tag
    is inserted in the DOM below the field.
  */
  showValidationErrors(formId, errors) {
    const form = document.getElementById(formId);
    Object.keys(errors).forEach((fieldName) => {
      if (Array.isArray(errors[fieldName])) {
        const fieldWrapper = form.querySelector(`#field-${fieldName}`);
        if (fieldWrapper) {
          let errorElem = fieldWrapper.querySelector('.mui-form__error');
          // If error P tag doesn't exist, create it
          if (!errorElem) {
            errorElem = document.createElement('p');
            errorElem.classList.add('mui-form__error');
          }
          [{ fieldName: errorElem.innerText }] = errors;
          const field = form.querySelector(`#${fieldName}`);
          // Insert the p tag below the field
          field.parentNode.appendChild(errorElem);
          // Add error class to field wrapper
          fieldWrapper.classList.add('has-error');
        }
      }
    });
  },
  showFormError(formid, error, alertBoxHtml) {
    const form = $(`#${formid}`);
    form
      .find('input[type="submit"]')
      .prop('disabled', false)
      .removeClass('submit-disabled');
    form
      .find('button[type="submit"]')
      .prop('disabled', false)
      .removeClass('submit-disabled');
    form.find('.loading').addClass('mui--hide');
    $('.alert').remove();
    form.append(alertBoxHtml);
    if (error.readyState === 4) {
      if (error.status === 500) {
        $(form).find('.alert__text').text(window.Hasgeek.Config.errorMsg.serverError);
      } else if (error.status === 429) {
        $(form)
          .find('.alert__text')
          .text(window.Hasgeek.Config.errorMsg.rateLimitError);
      } else if (error.responseJSON && error.responseJSON.error_description) {
        $(form).find('.alert__text').text(error.responseJSON.error_description);
      } else {
        $(form).find('.alert__text').text(window.Hasgeek.Config.errorMsg.error);
      }
    } else {
      $(form).find('.alert__text').text(window.Hasgeek.Config.errorMsg.networkError);
    }
  },
  ajaxFormSubmit(formId, url, onSuccess, onError, config) {
    $.ajax({
      url,
      type: 'POST',
      data: $(`#${formId}`).serialize(),
      dataType: config.dataType ? config.dataType : 'json',
      beforeSend() {
        Form.preventDoubleSubmit(formId);
        if (config.beforeSend) config.beforeSend();
      },
      success(responseData) {
        onSuccess(responseData);
      },
      error(xhr) {
        onError(xhr);
      },
    });
  },
  /* Takes formId, url, onSuccess, onError, config
   'formId' - Form id selector to query the DOM for the form
   'url' - The url to which the post request is sent
   'onSuccess' - A callback function that is executed if the request succeeds
   'onError' - A callback function that is executed if the request fails
   'config' -  An object that can contain dataType, beforeSend function
    handleFormSubmit handles form submit, serializes the form values,
      disables the submit button to prevent double submit,
      displays the loading indicator and submits the form via ajax.
      On completing the ajax request, calls the onSuccess/onError callback function.
  */
  handleFormSubmit(formId, url, onSuccess, onError, config) {
    $(`#${formId}`)
      .find('button[type="submit"]')
      .click((event) => {
        event.preventDefault();
        Form.ajaxFormSubmit(formId, url, onSuccess, onError, config);
      });
  },
};

export default Form;
