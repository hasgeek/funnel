import toastr from 'toastr';
import Form from './formhelper';

const FollowAccount = ({
  formId,
  postUrl = $(`#${formId}`).attr('action'),
  config = {},
  immediate = false,
}) => {
  const onSuccess = (response) => {
    $(`#${formId}`).find('button').prop('disabled', false);

    if (response.following) {
      $(`#${formId}`).find('button.js-unfollow-btn').removeClass('mui--hide');
      $(`#${formId}`).find('button.js-follow-btn').addClass('mui--hide');
      toastr.success(window.gettext('Your are now following this account'));
    } else {
      $(`#${formId}`).find('button.js-follow-btn').removeClass('mui--hide');
      $(`#${formId}`).find('button.js-unfollow-btn').addClass('mui--hide');
      toastr.success(window.gettext('You have unfollowed this account'));
    }
    Form.updateFormNonce(response);
  };

  const onError = (error) => {
    $(`#${formId}`).find('button').prop('disabled', false);
    const errorMsg = Form.handleAjaxError(error);
    toastr.error(errorMsg);
  };

  if (immediate) {
    Form.ajaxFormSubmit(formId, postUrl, onSuccess, onError, config);
  }
  Form.handleFormSubmit(formId, postUrl, onSuccess, onError, config);
  $(`#${formId}`).addClass('follow-action-activated');
};

function addFollowAction(btn, immediate = false) {
  const accountFollowConfig = {
    formId: $(btn).attr('id'),
    postUrl: $(btn).attr('action'),
    immediate,
  };
  FollowAccount(accountFollowConfig);
}

$(() => {
  $('.js-follow-form').each(function followButton() {
    addFollowAction(this);
  });
  $('body').on('click', '.js-follow-form', function handleFollow(event) {
    if (!$(this).hasClass('follow-action-activated')) {
      event.preventDefault();
      addFollowAction(this, true);
    }
  });
});
