import { precacheAndRoute } from 'workbox-precaching';
precacheAndRoute(self.__WB_MANIFEST);

workbox.core.skipWaiting();
workbox.core.clientsClaim();

workbox.routing.registerRoute(
  '/api/1/template/offline',
  new workbox.strategies.NetworkFirst({
    cacheName: 'offline',
  }),
  'GET'
);

workbox.routing.registerRoute(
  '/',
  new workbox.strategies.NetworkFirst({
    cacheName: 'homepage',
  }),
  'GET'
);

workbox.routing.registerRoute(
  new RegExp('/(.*)'),
  new workbox.strategies.NetworkOnly(),
  'GET'
);

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open('offline')
      .then((cache) => cache.addAll(['/api/1/template/offline']))
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    skipWaiting();
  }
});

workbox.routing.setCatchHandler(({ event }) => {
  switch (event.request.destination) {
    case 'document':
      return caches.match('/api/1/template/offline');
      break;

    default:
      return Response.error();
  }
});
