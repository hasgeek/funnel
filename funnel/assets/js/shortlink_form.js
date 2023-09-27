import toastr from 'toastr';
import Utils from './utils/helper';

$(() => {
  async function getShortlink(url) {
    const response = await fetch(window.Hasgeek.Config.shorturlApi, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        url,
      }).toString(),
    }).catch(() => {
      toastr.error(window.Hasgeek.Config.errorMsg.serverError);
    });
    if (response.ok) {
      const responseData = await response.json();
      $('.js-generated-url').text(responseData.shortlink);
      toastr.success(window.gettext('Shortlink generated'));
    } else {
      toastr.error(window.gettext('This URL is not valid for a shortlink'));
    }
  }

  $('.js-copy-shortlink').on('click', function clickCopyLink(event) {
    event.preventDefault();
    Utils.copyToClipboard('.js-generated-url');
  });

  $('#js-generate-shortlink').on('submit', (event) => {
    event.preventDefault();
    $('.js-generated-url').text();

    const url = $('.js-campaign-url').val();
    const id = $('.js-campaign-id').val();
    const source = $('.js-campaign-source').val();
    const medium = $('.js-campaign-medium').val();
    const name = $('.js-campaign-name').val();
    const term = $('.js-campaign-term').val();
    const content = $('.js-campaign-content').val();
    const campaignUrl = new URL(url);

    if (source) campaignUrl.searchParams.set('utm_source', source);
    if (medium) campaignUrl.searchParams.set('utm_medium', medium);
    if (name) campaignUrl.searchParams.set('utm_campaign', name);
    if (id) campaignUrl.searchParams.set('utm_id', id);
    if (term) campaignUrl.searchParams.set('utm_term', term);
    if (content) campaignUrl.searchParams.set('utm_content', content);
    getShortlink(campaignUrl.href);
  });
});
