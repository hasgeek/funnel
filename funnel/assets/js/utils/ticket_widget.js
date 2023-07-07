import { AJAX_TIMEOUT, RETRY_INTERVAL } from '../constants';
import Analytics from './analytics';

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
      timeout: AJAX_TIMEOUT,
      retries: 5,
      retryInterval: RETRY_INTERVAL,

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
              errorMsg = window.gettext('This device has no internet connection');
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
    $(document).on('boxofficeTicketingEvents', (event, userAction, label, value) => {
      Analytics.sendToGA('ticketing', userAction, label, value);
    });
    $(document).on(
      'boxofficeShowPriceEvent',
      (event, prices, currency, quantityAvailable) => {
        let price;
        let maxPrice;
        const isTicketAvailable =
          quantityAvailable.length > 0
            ? Math.min.apply(null, quantityAvailable.filter(Boolean))
            : 0;
        const minPrice = prices.length > 0 ? Math.min(...prices) : -1;
        if (!isTicketAvailable || minPrice < 0) {
          $('.js-tickets-available').addClass('mui--hide');
          $('.js-tickets-not-available').removeClass('mui--hide');
          $('.js-open-ticket-widget')
            .addClass('mui--is-disabled')
            .prop('disabled', true);
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
    this.urlHash = '#tickets';
    if (window.location.hash.indexOf(this.urlHash) > -1) {
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
      this.hideTicketModal();
    });
  },

  openTicketModal() {
    window.history.pushState(
      {
        openModal: true,
      },
      '',
      this.urlHash
    );
    $('.header').addClass('header--lowzindex');
    $('.tickets-wrapper__modal').addClass('tickets-wrapper__modal--show');
    $('.tickets-wrapper__modal').show();
  },

  hideTicketModal() {
    if ($('.tickets-wrapper__modal').hasClass('tickets-wrapper__modal--show')) {
      $('.header').removeClass('header--lowzindex');
      $('.tickets-wrapper__modal').removeClass('tickets-wrapper__modal--show');
      $('.tickets-wrapper__modal').hide();
      if (window.history.state.openModal) {
        window.history.back();
      }
    }
  },
};

export default Ticketing;
