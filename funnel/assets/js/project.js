import { Utils, TableSearch } from './util';
// import L from "leaflet";

// const defaultLatitude = '12.961443';

// const defaultLongitude = '77.64435000000003';

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

    this.trackBoxofficeEvents();
  },
  trackBoxofficeEvents() {
    $(document).on('boxofficeTicketingEvents', (event, userAction, label, value) => {
      Utils.sendToGA('ticketing', userAction, label, value);
    });
  },
};

// const EmbedMap = {
//   init(mapId) {
//     return true;
//     // let mapElem = `#${mapId}`;
//     // const TileLayer = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
//     // let $container = $(mapElem),
//     //   defaults = {
//     //     zoom: 17,
//     //     marker: [defaultLatitude, defaultLongitude],
//     //     label: null,
//     //     maxZoom: 18,
//     //     attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
//     //     subdomains: ['a', 'b', 'c'],
//     //     scrollWheelZoom: false,
//     //     dragging: false,
//     //   },
//     //   args,
//     //   options,
//     //   map,
//     //   marker;

//     // $container.empty();
//     // args = $container.data();
//     // if (args.markerlat && args.markerlng) {
//     //   args.marker = [args.markerlat, args.markerlng];
//     // }
//     // options = $.extend({
//     // }, defaults, args);

//     // map = new L.Map($container[0], {
//     //   center: options.center || options.marker,
//     //   zoom: options.zoom,
//     //   scrollWheelZoom: options.scrollWheelZoom,
//     //   dragging: options.dragging,
//     // });

//     // L.tileLayer(TileLayer, {
//     //   maxZoom: options.maxZoom,
//     //   attribution: options.attribution,
//     //   subdomains: options.subdomains,
//     // }).addTo(map);


//     // if (!args.tilelayer) {
//     //   marker = new L.marker(options.marker).addTo(map);
//     //   if (options.label) marker.bindPopup(options.label).openPopup();
//     // }
//   },
// };

$(() => {
  window.HasGeek.ProjectInit = function ({ticketing='', search=''}) {
    if (ticketing) {
      TicketWidget.init(ticketing);
    }

    // if (venue) {
    //   EmbedMap.init(venue.mapId);
    // }

    if (search) {
      let tableSearch = new TableSearch(search.tableId);
      let inputId = `#${search.inputId}`;
      let tableRow = `#${search.tableId} tbody tr`;
      $(inputId).keyup(function keyup() {
        if ($('.collapsible__body').css('display') === 'none') {
          $('.collapsible__header').click();
        }
        $(tableRow).addClass('mui--hide');
        let hits = tableSearch.searchRows($(this).val());
        $(hits.join(',')).removeClass('mui--hide');
      });
    }
  };
});
