import 'htmx.org';
import FollowAccount from './utils/follow_action';

$(() => {
  $('.js-follow-form').each(function followButton() {
    const accountFollowConfig = {
      formId: $(this).attr('id'),
      postUrl: $(this).attr('action'),
    };
    FollowAccount(accountFollowConfig);
  });
});
