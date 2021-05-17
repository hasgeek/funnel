import { Utils, SaveProject, Video } from './util';

const Ticketing = {
  init(tickets) {
    if (tickets.boxofficeUrl) {
      this.initBoxfficeWidget(tickets);
    }

    this.initTicketModal();
  },

  initBoxfficeWidget({
    boxofficeUrl,
    widgetElem,
    org,
    itemCollectionId,
    itemCollectionTitle,
  }) {
    let url;

    if (boxofficeUrl.slice(-1) === '/') {
      url = `${boxofficeUrl}boxoffice.js`;
    } else {
      url = `${boxofficeUrl}/boxoffice.js`;
    }

    $.get({
      url,
      crossDomain: true,
      timeout: window.Hasgeek.config.ajaxTimeout,
      retries: 5,
      retryInterval: window.Hasgeek.config.retryInterval,

      success(data) {
        const boxofficeScript = document.createElement('script');
        boxofficeScript.innerHTML = data.script;
        document.getElementsByTagName('body')[0].appendChild(boxofficeScript);
      },

      error(response) {
        const ajaxLoad = this;
        ajaxLoad.retries -= 1;
        let errorMsg;

        if (response.readyState === 4) {
          errorMsg = window.gettext(
            'The server is experiencing difficulties. Try again in a few minutes'
          );
          $(widgetElem).html(errorMsg);
        } else if (response.readyState === 0) {
          if (ajaxLoad.retries < 0) {
            if (!navigator.onLine) {
              errorMsg = window.gettext(
                'This device has no internet connection'
              );
            } else {
              errorMsg = window.gettext(
                'Unable to connect. If this device is behind a firewall or using any script blocking extension (like Privacy Badger), please ensure your browser can load boxoffice.hasgeek.com, api.razorpay.com and checkout.razorpay.com'
              );
            }

            $(widgetElem).html(errorMsg);
          } else {
            setTimeout(() => {
              $.get(ajaxLoad);
            }, ajaxLoad.retryInterval);
          }
        }
      },
    });
    window.addEventListener(
      'onBoxofficeInit',
      () => {
        window.Boxoffice.init({
          org,
          itemCollection: itemCollectionId,
          paymentDesc: itemCollectionTitle,
        });
      },
      false
    );
    $(document).on(
      'boxofficeTicketingEvents',
      (event, userAction, label, value) => {
        Utils.sendToGA('ticketing', userAction, label, value);
      }
    );
    $(document).on(
      'boxofficeShowPriceEvent',
      (event, prices, currency, quantityAvailable) => {
        let price, minPrice, maxPrice, isTicketAvailable;
        isTicketAvailable =
          quantityAvailable.length > 0 ? Math.min(...quantityAvailable) : 0;
        minPrice = prices.length > 0 ? Math.min(...prices) : 0;
        if (!isTicketAvailable || !minPrice) {
          $('.js-tickets-available').addClass('mui--hide');
          $('.js-tickets-not-available').removeClass('mui--hide');
          $('.js-open-ticket-widget').addClass('register-block__txt--strike');
        } else {
          price = `${currency}${minPrice}`;
          if (prices.length > 1) {
            maxPrice = Math.max(...prices);
            price = `${currency}${minPrice} - ${currency}${maxPrice}`;
          }
          $('.js-ticket-price').text(price);
        }
      }
    );
  },

  initTicketModal() {
    if (window.location.hash.indexOf('#tickets') > -1) {
      this.openTicketModal();
    }

    $('.js-open-ticket-widget').click((event) => {
      event.preventDefault();
      this.openTicketModal();
    });

    $('body').on('click', '#close-ticket-widget', (event) => {
      event.preventDefault();
      this.hideTicketModal();
    });

    $(window).on('popstate', () => {
      if (window.history.state.openModal) {
        this.hideTicketModal();
      } else if (window.history.state) {
        this.openTicketModal();
      }
    });
  },

  openTicketModal() {
    window.history.pushState(
      {
        openModal: true,
        prevUrl: window.location.href,
      },
      '',
      '#tickets'
    );
    $('.header').addClass('header--lowzindex');
    $('.tickets-wrapper__modal').addClass('tickets-wrapper__modal--show');
    $('.tickets-wrapper__modal').show();
  },

  hideTicketModal() {
    if (window.history.state.openModal) {
      window.history.pushState('', '', window.history.state.prevUrl);
      $('.header').removeClass('header--lowzindex');
      $('.tickets-wrapper__modal').removeClass('tickets-wrapper__modal--show');
      $('.tickets-wrapper__modal').hide();
    }
  },
};

$(() => {
  window.Hasgeek.ProjectHeaderInit = function init(
    saveProjectConfig = '',
    tickets = ''
  ) {
    if (saveProjectConfig) {
      SaveProject(saveProjectConfig);
    }

    $('.js-htmltruncate-expand').click(function (event) {
      event.preventDefault();
      $(this).addClass('mui--hide');
      $(this).next('.js-htmltruncate-full').removeClass('mui--hide');
    });

    // Adding the embed video player
    if ($('.js-embed-video').length > 0) {
      $('.js-embed-video').each(function () {
        let videoUrl = $(this).data('video-src');
        Video.embedIframe(this, videoUrl);
      });
    }

    $('a.js-register-btn').click(function () {
      $(this).modal('show');
    });

    if (window.location.hash.includes('register-modal')) {
      $('a.js-register-btn').modal('show');
    }

    if (tickets) {
      Ticketing.init(tickets);
    }
  };
});
