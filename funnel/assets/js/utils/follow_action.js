import toastr from 'toastr';
import Form from './formhelper';

const handleFollow = (thisForm) => {
  const accountID = $(thisForm).data('account-id');
  const $accountFollowForms = $(`form[data-account-id=${accountID}]`);

  $accountFollowForms.find('button').prop('disabled', false);
  const formId = $(thisForm).attr('id');
  const postUrl = $(thisForm).attr('action');

  const config = {};
  config.formData = new URLSearchParams({
    follow: $(thisForm).find('input[name="follow"]').val(),
    csrf_token: $('meta[name="csrf-token"]').attr('content'),
  }).toString();

  const onSuccess = (response) => {
    $accountFollowForms.find('button').prop('disabled', false);

    if (response.following) {
      $accountFollowForms.find('button.js-unfollow-btn').removeClass('mui--hide');
      $accountFollowForms.find('button.js-follow-btn').addClass('mui--hide');
      toastr.success(window.gettext('Your are now following this account'));
    } else {
      $accountFollowForms.find('button.js-follow-btn').removeClass('mui--hide');
      $accountFollowForms.find('button.js-unfollow-btn').addClass('mui--hide');
      toastr.success(window.gettext('You have unfollowed this account'));
    }
  };

  const onError = (error) => {
    $accountFollowForms.find('button').prop('disabled', false);
    const errorMsg = Form.handleAjaxError(error);
    toastr.error(errorMsg);
  };

  Form.ajaxFormSubmit(formId, postUrl, onSuccess, onError, config);
};

$(() => {
  $('html.userlogin body').on('click', '.js-follow-form', function follow(event) {
    event.preventDefault();
    handleFollow(this);
  });
});
