import { Utils, SaveProject } from './util';
import L from "leaflet";

const TicketWidget = {
  init({ boxofficeUrl, widgetElem, org, itemCollectionId, itemCollectionTitle }) {
    let url;
    if (boxofficeUrl.slice(-1) === '/') {
      url = `${boxofficeUrl}boxoffice.js`;
    } else {
      url = `${boxofficeUrl}/boxoffice.js`;
    }
    $.get({
      url,
      crossDomain: true,
      timeout: 8000,
      retries: 5,
      retryInterval: 8000,
      success(data) {
        let boxofficeScript = document.createElement('script');
        boxofficeScript.innerHTML = data.script;
        document.getElementsByTagName('body')[0].appendChild(boxofficeScript);
      },
      error(response) {
        let ajaxLoad = this;
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
              errorMsg = '<p>Unable to connect. If you are behind a firewall or using any script blocking extension (like Privacy Badger), please ensure your browser can load boxoffice.hasgeek.com, api.razorpay.com and checkout.razorpay.com .</p>';
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

    window.addEventListener('onBoxofficeInit', () => {
      window.Boxoffice.init({
        org,
        itemCollection: itemCollectionId,
        paymentDesc: itemCollectionTitle,

      });
    }, false);

    this.initTicketModal();
    this.trackBoxofficeEvents();
  },
  trackBoxofficeEvents() {
    $(document).on('boxofficeTicketingEvents', (event, userAction, label, value) => {
      Utils.sendToGA('ticketing', userAction, label, value);
    });
  },
  initTicketModal() {
    $('.open-ticket-widget').click(event => {
      event.preventDefault();
      this.openTicketModal();
    });

    $('#close-ticket-widget').click(event => {
      event.preventDefault();
      this.hideTicketModal();
    });

    if (window.location.hash.indexOf('#tickets') > -1) {
      if ($(window).width() < 768) {
        this.openTicketModal();
      } else {
        Utils.animateScrollTo($('#tickets').offset().top);
      }
    }

    $(window).resize(() => {
      if ($(window).width() > 767 && $('.about__participate').hasClass('about__participate--modal')) {
        this.hideTicketModal();
      }
    });

    $(window).on('popstate', () => {
      if($(window).width() < 767 && $('.about__participate').hasClass('about__participate--modal')) {
        this.hideTicketModal();
      } else if(window.history.state) {
        this.openTicketModal();
      }
    });
  },
  openTicketModal() {
    let url = window.location.href;
    if (url.indexOf('#tickets') < 0) {
      url = `${window.location.pathname}#tickets${window.location.search}`;
    }
    window.history.pushState({openModal: true}, '', url);
    $('.header').removeClass('header--fixed');
    $('.about__participate').addClass('about__participate--modal');
    $('.about__participate').fadeIn();
  },
  hideTicketModal() {
    let url = window.location.href.replace('#tickets', '');
    window.history.pushState('', '', url);
    $('.header').addClass('header--fixed');
    $('.about__participate').removeClass('about__participate--modal');
    $('.about__participate').fadeOut();
  },
};

const EmbedMap = {
  init({mapId, latitude, longitude}) {
    let mapElem = `#${mapId}`;
    const TileLayer = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    let $container = $(mapElem),
      defaults = {
        zoom: 17,
        marker: [latitude, longitude],
        label: null,
        maxZoom: 18,
        attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
        subdomains: ['a', 'b', 'c'],
        scrollWheelZoom: false,
        dragging: false,
      },
      args,
      options,
      map,
      marker;

    $container.empty();
    args = $container.data();
    if (args.markerlat && args.markerlng) {
      args.marker = [args.markerlat, args.markerlng];
    }
    options = $.extend({
    }, defaults, args);

    map = new L.Map($container[0], {
      center: options.center || options.marker,
      zoom: options.zoom,
      scrollWheelZoom: options.scrollWheelZoom,
      dragging: options.dragging,
    });

    L.tileLayer(TileLayer, {
      maxZoom: options.maxZoom,
      attribution: options.attribution,
      subdomains: options.subdomains,
    }).addTo(map);


    if (!args.tilelayer) {
      marker = new L.marker(options.marker).addTo(map);
      if (options.label) marker.bindPopup(options.label).openPopup();
    }
  },
};

$(() => {
  window.HasGeek.ProjectInit = function ({ticketing='', venue= '', saveProjectConfig=''}) {
    if (ticketing) {
      TicketWidget.init(ticketing);
    }

    if (venue) {
      EmbedMap.init(venue);
    }

    if (saveProjectConfig) {
      SaveProject(saveProjectConfig);
    }

    $('.truncate').succinct({
      size: 150
    });
  };
});
