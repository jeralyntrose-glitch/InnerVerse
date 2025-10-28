const CACHE_NAME = 'innerverse-chat-v5';
const urlsToCache = [
  '/manifest.json',
  '/chat', // Cached for offline fallback only
  '/brain-icon-192.png',
  '/brain-icon-512.png',
  '/brain-icon-980.png',
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
  
  // Network-first for API calls - ALWAYS fetch fresh, no caching
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/claude/')) {
    event.respondWith(fetch(event.request));
    return;
  }
  
  // Allow caching for CDN libraries
  const isCDNLibrary = url.host === 'cdn.jsdelivr.net' || 
                       url.host === 'fonts.googleapis.com' ||
                       url.host === 'fonts.gstatic.com';
  
  // Network-first for HTML/JS files (except CDN) - fetch fresh, update cache, fallback to cache offline
  if ((url.pathname.endsWith('.html') || url.pathname.endsWith('.js') || 
       url.pathname === '/chat' || url.pathname === '/') && !isCDNLibrary) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Update cache with fresh version
          if (response && response.status === 200) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
          }
          return response;
        })
        .catch(() => {
          // Offline fallback - try cached version first
          return caches.match(event.request).then((cached) => {
            if (cached) return cached;
            
            // For navigation requests, fall back to /chat shell
            if (event.request.mode === 'navigate') {
              return caches.match('/chat');
            }
            
            // For scripts/assets, fail gracefully (don't return HTML as JS)
            return new Response('Offline - resource not cached', {
              status: 503,
              statusText: 'Service Unavailable'
            });
          });
        })
    );
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
        // Offline fallback for static assets
        if (event.request.mode === 'navigate') {
          return caches.match('/chat');
        }
        // Return undefined for other failed requests
        return undefined;
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
