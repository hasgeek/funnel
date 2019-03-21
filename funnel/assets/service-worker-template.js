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

/* The service worker handles all fetch requests. If fetching of page fails due to a network error, 
it will return the cached "offline" page. */
workbox.routing.registerRoute(new RegExp('/(.*)'), args => {
  return new workbox.strategies.NetworkFirst({cacheName: 'routes'}).handle(args).then(response => {
    if (!response) {
      return caches.match('/offline');
    } 
    return response;
  });
});

// https://googlechrome.github.io/samples/service-worker/custom-offline-page/
function createCacheBustedRequest(url) {
  let request = new Request(url, {cache: 'reload'});
  // See https://fetch.spec.whatwg.org/#concept-request-mode
  /* This is not yet supported in Chrome as of M48, so we need to 
  explicitly check to see if the cache: 'reload' option had any effect.*/
  if ('cache' in request) {
    return request;
  }

  // If {cache: 'reload'} didn't have any effect, append a cache-busting URL parameter instead.
  let bustedUrl = new URL(url, self.location.href);
  bustedUrl.search += (bustedUrl.search ? '&' : '') + 'cachebust=' + Date.now();
  return new Request(bustedUrl);
}

// Cache the offline page during install phase of the service worker
self.addEventListener('install', event => {
  event.waitUntil(
    fetch(createCacheBustedRequest('/api/1/template/offline')).then(function(response) {
      return caches.open('hasgeek-offline').then(function(cache) {
        return cache.put('offline', response);
      });
    })
  );
});
