import toastr from 'toastr';
import Utils from './utils/helper';

$(() => {
  const form = '#js-generate-shortlink';
  const shortlinkBox = '.js-generated-url';
  const copyBtn = '.js-copy-shortlink';

  async function getShortlink(url) {
    $(form).find('.loading').removeClass('mui--hide');
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
    if (response && response.ok) {
      const responseData = await response.json();
      $(shortlinkBox).text(responseData.shortlink);
      toastr.success(window.gettext('Shortlink generated'));
    } else {
      toastr.error(window.gettext('This URL is not valid for a shortlink'));
    }
    $(form).find('.loading').addClass('mui--hide');
  }

  $(copyBtn).on('click', function clickCopyLink(event) {
    event.preventDefault();
    Utils.copyToClipboard($(shortlinkBox)[0]);
  });

  $(form).on('submit', (event) => {
    event.preventDefault();
    // Clear shortlink url box
    $(shortlinkBox).text();

    const url = $('.js-campaign-url').val();
    const id = $('.js-campaign-id').val();
    const source = $('.js-campaign-source').val();
    const medium = $('.js-campaign-medium').val();
    const name = $('.js-campaign-name').val();
    const term = $('.js-campaign-term').val();
    const content = $('.js-campaign-content').val();
    try {
      const campaignUrl = new URL(url);
      if (source) campaignUrl.searchParams.set('utm_source', source);
      if (medium) campaignUrl.searchParams.set('utm_medium', medium);
      if (name) campaignUrl.searchParams.set('utm_campaign', name);
      if (id) campaignUrl.searchParams.set('utm_id', id);
      if (term) campaignUrl.searchParams.set('utm_term', term);
      if (content) campaignUrl.searchParams.set('utm_content', content);
      getShortlink(campaignUrl.href);
    } catch (e) {
      toastr.error(window.gettext('This URL is not valid for a shortlink'));
    }
  });
});
