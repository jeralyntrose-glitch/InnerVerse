const CACHE_NAME = 'innerverse-chat-v6';
const urlsToCache = [
  '/manifest.json',
  '/brain-icon-192.png',
  '/brain-icon-512.png',
  // CDN libraries for offline support
  'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
  'https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap'
];

self.addEventListener('install', (event) => {
  // Force this service worker to activate immediately
  console.log('[SW v6] Installing...');
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW v6] Caching essential files only');
        return cache.addAll(urlsToCache).catch(err => {
          console.error('[SW v6] Cache failed for some files:', err);
        });
      })
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Network-ONLY for all HTML pages and API calls - NEVER cache these!
  if (url.pathname.startsWith('/api/') || 
      url.pathname.startsWith('/claude/') ||
      url.pathname === '/chat' ||
      url.pathname === '/claude' ||
      url.pathname === '/' ||
      url.pathname.endsWith('.html')) {
    console.log('[SW v6] Network-ONLY:', url.pathname);
    event.respondWith(fetch(event.request));
    return;
  }
  
  // Allow caching for CDN libraries
  const isCDNLibrary = url.host === 'cdn.jsdelivr.net' || 
                       url.host === 'fonts.googleapis.com' ||
                       url.host === 'fonts.gstatic.com';
  
  // Network-first for local JS files (except CDN)
  if (url.pathname.endsWith('.js') && !isCDNLibrary) {
    console.log('[SW v6] Network-first for JS:', url.pathname);
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
          }
          return response;
        })
        .catch(() => caches.match(event.request))
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
  console.log('[SW v6] Activating...');
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      console.log('[SW v6] Found caches:', cacheNames);
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            console.log('[SW v6] ❌ DELETING old cache:', cacheName);
            return caches.delete(cacheName);
          } else {
            console.log('[SW v6] ✅ Keeping cache:', cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW v6] Taking control of all clients');
      return self.clients.claim();
    })
  );
});
