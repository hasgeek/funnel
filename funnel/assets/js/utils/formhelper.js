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
  activateToggleSwitch(checkboxId, callbckfn = '') {
    function postForm() {
      let submitting = false;
      return (checkboxElem) => {
        if (!submitting) {
          submitting = true;
          const checkbox = $(checkboxElem);
          const currentState = checkboxElem.checked;
          const previousState = !currentState;
          const formData = new FormData(checkbox.parent('form')[0]);
          if (!currentState) {
            formData.append(checkbox.attr('name'), false);
          }

          fetch(checkbox.parent('form').attr('action'), {
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
              submitting = false;
            })
            .catch((error) => {
              Form.handleAjaxError(error);
              checkbox.prop('checked', previousState);
              submitting = false;
            });
        }
      };
    }

    const throttleSubmit = postForm();

    $('body').on('change', checkboxId, function submitToggleSwitch() {
      throttleSubmit(this);
    });

    $('body').on('click', '.js-dropdown-toggle', function stopPropagation(event) {
      event.stopPropagation();
    });
  },
  openSubmissionToggle(checkboxId, cfpStatusDiv) {
    const onSuccess = () => {
      $(cfpStatusDiv).toggleClass('mui--hide');
    };
    Form.activateToggleSwitch(checkboxId, onSuccess);
  },
  activate_select2() {
    /* Upgrade to jquery 3.6 select2 autofocus isn't working. This is to fix that problem.
      select2/select2#5993  */
    $(document).on('select2:open', () => {
      document.querySelector('.select2-search__field').focus();
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
  lastuserAutocomplete(options) {
    const assembleUsers = function (users) {
      return users.map((user) => {
        return { id: user.buid, text: user.label };
      });
    };

    $(`#${options.id}`).select2({
      placeholder: 'Search for a user',
      multiple: options.multiple,
      minimumInputLength: 2,
      ajax: {
        url: options.autocomplete_endpoint,
        dataType: 'jsonp',
        data(params) {
          if ('client_id' in options) {
            return {
              q: params.term,
              client_id: options.client_id,
              session: options.session_id,
            };
          }
          return {
            q: params.term,
          };
        },
        processResults(data) {
          let users = [];
          if (data.status === 'ok') {
            users = assembleUsers(data.users);
          }
          return { more: false, results: users };
        },
      },
    });
  },
  textAutocomplete(options) {
    $(`#${options.id}`).select2({
      placeholder: 'Type to select',
      multiple: options.multiple,
      minimumInputLength: 2,
      ajax: {
        url: options.autocomplete_endpoint,
        dataType: 'json',
        data(params, page) {
          return {
            q: params.term,
            page,
          };
        },
        processResults(data) {
          return {
            more: false,
            results: data[options.key].map((item) => {
              return { id: item, text: item };
            }),
          };
        },
      },
    });
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
        window.Hasgeek.Forms.preventDoubleSubmit(formId);
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
        window.Hasgeek.Forms.ajaxFormSubmit(formId, url, onSuccess, onError, config);
      });
  },
  activate_geoname_autocomplete(selector, autocompleteEndpoint, getnameEndpoint) {
    $(selector).select2({
      placeholder: 'Search for a location',
      multiple: true,
      minimumInputLength: 2,
      ajax: {
        url: autocompleteEndpoint,
        dataType: 'jsonp',
        data(params) {
          return {
            q: params.term,
          };
        },
        processResults(data) {
          const rdata = [];
          if (data.status === 'ok') {
            for (let i = 0; i < data.result.length; i += 1) {
              rdata.push({
                id: data.result[i].geonameid,
                text: data.result[i].picker_title,
              });
            }
          }
          return { more: false, results: rdata };
        },
      },
    });

    // Setting label for Geoname ids
    let val = $(selector).val();
    if (val) {
      val = val.map((id) => {
        return `name=${id}`;
      });
      const qs = val.join('&');
      $.ajax(`${getnameEndpoint}?${qs}`, {
        accepts: 'application/json',
        dataType: 'jsonp',
      }).done((data) => {
        $(selector).empty();
        const rdata = [];
        if (data.status === 'ok') {
          for (let i = 0; i < data.result.length; i += 1) {
            $(selector).append(
              `<option value="${data.result[i].geonameid}" selected>${data.result[i].picker_title}</option>`
            );
            rdata.push(data.result[i].geonameid);
          }
          $(selector).val(rdata).trigger('change');
        }
      });
    }
  },
};

export default Form;
