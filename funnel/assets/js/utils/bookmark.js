import Form from './formhelper';

const SaveProject = ({
  formId,
  postUrl = $(`#${formId}`).attr('action'),
  config = {},
}) => {
  const onSuccess = (response) => {
    $(`#${formId}`)
      .find('button')
      .prop('disabled', false)
      .removeClass('animate-btn--animate');

    $(`#${formId}`)
      .find('button')
      .each(function showSaveProgress() {
        if ($(this).hasClass('animate-btn--show')) {
          $(this).removeClass('animate-btn--show');
        } else {
          $(this).addClass('animate-btn--show');
          if ($(this).hasClass('animate-btn--saved')) {
            $(this).addClass('animate-btn--animate');
            window.toastr.success(
              window.gettext('Project added to Account > Saved projects')
            );
          }
        }
      });
    Form.updateFormNonce(response);
  };

  const onError = (response) => Form.handleAjaxError(response);

  window.Hasgeek.Forms.handleFormSubmit(formId, postUrl, onSuccess, onError, config);
};

export default SaveProject;
