import toastr from 'toastr';
import Utils from './helper';

const WebShare = {
  addWebShare() {
    if (navigator.share) {
      $('.project-links').hide();
      $('.hg-link-btn').removeClass('mui--hide');

      const mobileShare = (title, url, text) => {
        navigator.share({
          title,
          url,
          text,
        });
      };

      $('body').on('click', '.hg-link-btn', function clickWebShare(event) {
        event.preventDefault();
        let url =
          $(this).data('url') ||
          (document.querySelector('link[rel=canonical]') &&
            document.querySelector('link[rel=canonical]').href) ||
          window.location.href;
        const title = $(this).data('title') || document.title;
        const text = $(this).data('text') || '';
        if ($(this).attr('data-shortlink')) {
          mobileShare(title, url, text);
        } else {
          Utils.fetchShortUrl(url)
            .then((shortlink) => {
              url = shortlink;
              $(this).attr('data-shortlink', true);
            })
            .finally(() => {
              mobileShare(title, url, text);
            });
        }
      });
    } else {
      $('body').on('click', '.js-copy-link', function clickCopyLink(event) {
        event.preventDefault();
        if ($(this).attr('data-shortlink')) {
          Utils.copyToClipboard($(this).find('.js-copy-url')[0]);
        } else {
          Utils.fetchShortUrl($(this).find('.js-copy-url').first().html())
            .then((shortlink) => {
              $(this).find('.js-copy-url').text(shortlink);
              $(this).attr('data-shortlink', true);
              Utils.copyToClipboard($(this).find('.js-copy-url')[0]);
            })
            .catch((errMsg) => {
              toastr.error(errMsg);
            });
        }
      });
    }
  },
  enableWebShare() {
    if (navigator.share) {
      $('.project-links').hide();
      $('.hg-link-btn').removeClass('mui--hide');
    }
  },
};

export default WebShare;
