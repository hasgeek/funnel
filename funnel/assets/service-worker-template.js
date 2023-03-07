import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute, setCatchHandler } from 'workbox-routing';
import { NetworkFirst, NetworkOnly } from 'workbox-strategies';
import { skipWaiting, clientsClaim } from 'workbox-core';
const filteredManifest = self.__WB_MANIFEST.filter((entry) => {
  return !entry.url.match('prism-');
});

precacheAndRoute(filteredManifest);

skipWaiting();
clientsClaim();

registerRoute(
  '/api/1/template/offline',
  new NetworkFirst({
    cacheName: 'offline',
  }),
  'GET'
);

registerRoute(
  '/',
  new NetworkFirst({
    cacheName: 'homepage',
  }),
  'GET'
);

registerRoute(new RegExp('/(.*)'), new NetworkOnly(), 'GET');

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('offline').then((cache) => cache.addAll(['/api/1/template/offline']))
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    skipWaiting();
  }
});

setCatchHandler(({ event }) => {
  switch (event.request.destination) {
    case 'document':
      return caches.match('/api/1/template/offline');
      break;

    default:
      return Response.error();
  }
});
