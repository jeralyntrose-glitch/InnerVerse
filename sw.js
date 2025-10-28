// Service Worker disabled - unregister itself
self.addEventListener('install', () => {
  console.log('[SW] Uninstalling...');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('[SW] Cleaning up and unregistering...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          console.log('[SW] Deleting cache:', cacheName);
          return caches.delete(cacheName);
        })
      );
    }).then(() => {
      return self.registration.unregister();
    })
  );
});

// Pass through all requests - no caching
self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});
