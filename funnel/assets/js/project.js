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
  };
});
