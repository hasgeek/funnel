workbox.core.skipWaiting();
workbox.core.clientsClaim();

workbox.precaching.precacheAndRoute(self.__precacheManifest);

workbox.routing.registerRoute(new RegExp('/^https?\:\/\/static.*/'), new workbox.strategies.NetworkFirst({
  "cacheName": "assets"
}), 'GET');

workbox.routing.registerRoute(new RegExp('/^https?:\/\/hasgeek.com\/*/'), new workbox.strategies.NetworkFirst({
  "cacheName": "assets"
}), 'GET');

//For development setup caching of assets
workbox.routing.registerRoute(new RegExp('/^http:\/\/localhost:3000\/static/'), new workbox.strategies.NetworkFirst({
  "cacheName": "baseframe-local"
}), 'GET');

workbox.routing.registerRoute(new RegExp('/^https?:\/\/images\.hasgeek\.com\/embed\/file\/*/'), new workbox.strategies.NetworkFirst({
  "cacheName": "images"
}), 'GET');

workbox.routing.registerRoute(new RegExp('/^https?:\/\/fonts.googleapis.com\/*/'), new workbox.strategies.NetworkFirst({
  "cacheName": "fonts"
}), 'GET');

workbox.routing.registerRoute(new RegExp('/^https?\:\/\/ajax.googleapis.com\/*/'), new workbox.strategies.NetworkFirst({
  "cacheName": "cdn-libraries"
}), 'GET');

workbox.routing.registerRoute(new RegExp('/(.*)'), new workbox.strategies.NetworkFirst({
  "cacheName": "routes"
}), 'GET');

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open('offline').then((cache) => cache.addAll(['/api/1/template/offline'])));
});

addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    skipWaiting();
  }
});

workbox.routing.setCatchHandler(({event}) => {
  switch (event.request.destination) {
    case 'document':
      return caches.match('offline');
    break;

    default:
      return Response.error();
  }
});
