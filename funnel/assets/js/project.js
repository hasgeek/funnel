import L from 'leaflet';
import initEmbed from './utils/initembed';

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
    let marker;
    $container.empty();
    const args = $container.data();

    if (args.markerlat && args.markerlng) {
      args.markerLatLng = [args.markerlat, args.markerlng];
    }

    const options = $.extend({}, defaults, args);
    const map = new L.Map($container[0], {
      center: options.center || options.markerLatLng,
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
      marker = new L.Marker(options.markerLatLng).addTo(map);
      if (options.label) marker.bindPopup(options.label).openPopup();
    }
  },
};
$(() => {
  window.Hasgeek.projectInit = ({ venue = '', markdownElem = '' }) => {
    if (venue) {
      EmbedMap.init(venue);
    }
    // Include parent container
    initEmbed(markdownElem);
  };
});
