const CACHE_NAME = 'innerverse-chat-v2';
const urlsToCache = [
  '/manifest.json',
  '/chat',
  '/brain-icon-192.png',
  '/brain-icon-512.png',
  // CDN libraries for offline support
  'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
  'https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Service Worker: Caching files');
        return cache.addAll(urlsToCache).catch(err => {
          console.error('Service Worker: Cache failed for some files:', err);
        });
      })
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Skip caching for API calls - always fetch fresh
  if (url.pathname.startsWith('/api/') || 
      url.pathname.startsWith('/claude/')) {
    event.respondWith(fetch(event.request));
    return;
  }
  
  // Allow caching for CDN libraries
  const isCDNLibrary = url.host === 'cdn.jsdelivr.net' || 
                       url.host === 'fonts.googleapis.com' ||
                       url.host === 'fonts.gstatic.com';
  
  // Skip caching for non-CDN JS files (dynamic scripts)
  if (url.pathname.includes('.js') && !isCDNLibrary) {
    event.respondWith(fetch(event.request));
    return;
  }
  
  // Cache-first strategy for static assets (HTML, CSS, images, manifest)
  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          // Return cached version but update cache in background
          fetch(event.request).then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(event.request, networkResponse);
              });
            }
          }).catch(() => {});
          return cachedResponse;
        }
        
        // Not in cache, fetch from network
        return fetch(event.request).then((networkResponse) => {
          // Cache successful responses
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
          }
          return networkResponse;
        });
      })
      .catch(() => {
        // Offline fallback - return cached chat page
        if (event.request.mode === 'navigate') {
          return caches.match('/chat');
        }
      })
  );
});

self.addEventListener('activate', (event) => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            console.log('Service Worker: Clearing old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  return self.clients.claim();
});
