import toastr from 'toastr';
import Form from './formhelper';

const FollowAccount = ({
  formId,
  postUrl = $(`#${formId}`).attr('action'),
  config = {},
}) => {
  const onSuccess = (response) => {
    $(`#${formId}`).find('button').prop('disabled', false);

    if (response.following) {
      $('.js-unfollow-btn').removeClass('mui--hide');
      $('.js-follow-btn').addClass('mui--hide');
      toastr.success(window.gettext('Your are now following this account'));
    } else {
      $('.js-follow-btn').removeClass('mui--hide');
      $('.js-unfollow-btn').addClass('mui--hide');
      toastr.success(window.gettext('You have unfollowed this account'));
    }
    Form.updateFormNonce(response);
  };

  const onError = (error) => {
    const errorMsg = Form.handleAjaxError(error);
    toastr.error(errorMsg);
  };

  Form.handleFormSubmit(formId, postUrl, onSuccess, onError, config);
};

export default FollowAccount;
