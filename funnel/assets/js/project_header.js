import SaveProject from './utils/bookmark';
import Video from './utils/embedvideo';
import Analytics from './utils/analytics';
import Spa from './utils/spahelper';
import { Widgets } from './utils/formWidgets';
import initEmbed from './utils/initembed';
import SortItem from './utils/sort';

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
      timeout: window.Hasgeek.Config.ajaxTimeout,
      retries: 5,
      retryInterval: window.Hasgeek.Config.retryInterval,

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

$(() => {
  window.Hasgeek.projectHeaderInit = (
    projectTitle,
    saveProjectConfig = '',
    tickets = '',
    toggleId = '',
    sort = ''
  ) => {
    if (saveProjectConfig) {
      SaveProject(saveProjectConfig);
    }

    $('body').on('click', '.js-htmltruncate-expand', function expandTruncation(event) {
      event.preventDefault();
      $(this).addClass('mui--hide');
      $(this).next('.js-htmltruncate-full').removeClass('mui--hide');
      initEmbed($(this).next('.js-htmltruncate-full'));
    });

    // Adding the embed video player
    if ($('.js-embed-video').length > 0) {
      $('.js-embed-video').each(function addEmbedVideoPlayer() {
        const videoUrl = $(this).data('video-src');
        Video.embedIframe(this, videoUrl);
      });
    }

    $('a.js-register-btn').click(function showRegistrationModal() {
      $(this).modal('show');
    });

    if (window.location.hash.includes('register-modal')) {
      $('a.js-register-btn').modal('show');
    }

    if (tickets) {
      Ticketing.init(tickets);
    }

    if (toggleId) {
      Widgets.activateToggleSwitch(toggleId);
    }

    if (sort?.url) {
      SortItem($(sort.wrapperElem), sort.placeholder, sort.url);
    }

    const hightlightNavItem = (navElem) => {
      const navHightlightClass = 'sub-navbar__item--active';
      $('.sub-navbar__item').removeClass(navHightlightClass);
      $(`#${navElem}`).addClass(navHightlightClass);

      if (window.Hasgeek.subpageTitle) {
        $('body').addClass('subproject-page');
        if (window.Hasgeek.subpageHasVideo) {
          $('body').addClass('mobile-hide-livestream');
        } else {
          $('body').removeClass('mobile-hide-livestream');
        }
      } else {
        $('body').removeClass('subproject-page').removeClass('mobile-hide-livestream');
      }
    };

    const currentnavItem = $('.sub-navbar__item--active').attr('id');
    Spa.init(projectTitle, currentnavItem, hightlightNavItem);

    $('body').on('click', '.js-spa-navigate', function pageRefresh(event) {
      event.preventDefault();
      const url = $(this).attr('href');
      Spa.fetchPage(url, $(this).attr('id'), true);
    });
  };
});
