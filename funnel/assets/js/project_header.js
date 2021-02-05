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
          errorMsg = 'Server error, please try again later.';
          $(widgetElem).html(errorMsg);
        } else if (response.readyState === 0) {
          if (ajaxLoad.retries < 0) {
            if (!navigator.onLine) {
              errorMsg = 'Unable to connect. There is no network!';
            } else {
              errorMsg =
                '<p>Unable to connect. If you are behind a firewall or using any script blocking extension (like Privacy Badger), please ensure your browser can load boxoffice.hasgeek.com, api.razorpay.com and checkout.razorpay.com .</p>';
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
  },

  initTicketModal() {
    $('.js-open-ticket-widget').click((event) => {
      console.log('clicked');
      event.preventDefault();
      this.openTicketModal();
    });
    $('#close-ticket-widget').click((event) => {
      event.preventDefault();
      this.hideTicketModal();
    });

    if (window.location.hash.indexOf('#tickets') > -1) {
      this.openTicketModal();
    }

    $(window).resize(() => {
      if (
        $(window).width() >= window.Hasgeek.config.mobileBreakpoint &&
        $('.tickets-wrapper__modal').hasClass('tickets-wrapper__modal--show')
      ) {
        this.hideTicketModal();
      }
    });
    $(window).on('popstate', () => {
      if (
        $(window).width() < window.Hasgeek.config.mobileBreakpoint &&
        $('.tickets-wrapper__modal ').hasClass('tickets-wrapper__modal--show')
      ) {
        this.hideTicketModal();
      } else if (
        window.history.state &&
        $(window).width() < window.Hasgeek.config.mobileBreakpoint
      ) {
        this.openTicketModal();
      }
    });
  },

  openTicketModal() {
    window.history.pushState(
      {
        openModal: true,
      },
      '',
      '#tickets'
    );
    console.log('open widget');
    $('.header').addClass('header--lowzindex');
    $('.tickets-wrapper__modal').addClass('tickets-wrapper__modal--show');
    $('.tickets-wrapper__modal').fadeIn();
  },

  hideTicketModal() {
    window.history.pushState(
      '',
      '',
      window.location.pathname + window.location.search
    );
    $('.header').removeClass('.header--lowzindex');
    $('.tickets-wrapper__modal').removeClass('tickets-wrapper__modal--show');
    $('.tickets-wrapper__modal').fadeOut();
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

    // Adding the embed video player
    if ($('.js-embed-video').length > 0) {
      $('.js-embed-video').each(function () {
        let videoUrl = $(this).data('video-src');
        Video.embedIframe(this, videoUrl);
      });
    }

    $('a#register-btn').click(function () {
      $(this).modal();
    });

    if (window.location.hash === '#register-modal') {
      $('a#register-btn').modal();
    }

    if (tickets) {
      Ticketing.init(tickets);
    }
  };
});
