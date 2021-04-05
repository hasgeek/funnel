/* global vegaEmbed */

import L from 'leaflet';

const EmbedMap = {
  init({ mapId, latitude, longitude }) {
    const mapElem = `#${mapId}`;
    const TileLayer = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    const $container = $(mapElem);
    const defaults = {
      zoom: 17,
      marker: [latitude, longitude],
      label: null,
      maxZoom: 18,
      attribution:
        'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
      subdomains: ['a', 'b', 'c'],
      scrollWheelZoom: false,
      dragging: false,
    };
    let args;
    let options;
    let map;
    let marker;
    $container.empty();
    args = $container.data();

    if (args.markerlat && args.markerlng) {
      args.marker = [args.markerlat, args.markerlng];
    }

    options = $.extend({}, defaults, args);
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
  window.Hasgeek.ProjectInit = function ({ venue = '' }) {
    if (venue) {
      EmbedMap.init(venue);
    }
    if ($('.language-vega-lite').length > 0) {
      let vegaliteCDN = [
        'https://cdn.jsdelivr.net/npm/vega@5',
        'https://cdn.jsdelivr.net/npm/vega-lite@5',
        'https://cdn.jsdelivr.net/npm/vega-embed@6',
      ];
      let vegaliteUrl = 0;
      let loadVegaScript = function () {
        $.getScript({ url: vegaliteCDN[vegaliteUrl], cache: true }).success(
          function () {
            if (vegaliteUrl < vegaliteCDN.length) {
              vegaliteUrl += 1;
              loadVegaScript();
            }
            // Once all vega js is loaded, initialize vega visualization on all pre tags with class 'language-vega-lite'
            if (vegaliteUrl === vegaliteCDN.length) {
              $('.language-vega-lite').each(function () {
                vegaEmbed(this, JSON.parse($(this).find('code').text()));
              });
            }
          }
        );
      };
      loadVegaScript();
    }
  };
});
