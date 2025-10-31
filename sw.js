// Minimal Service Worker - Just for PWA Installation
// No offline caching, no complex features

const CACHE_NAME = 'innerverse-v2-zindex-fix';

// Install event - required for PWA
self.addEventListener('install', (event) => {
  console.log('✅ Service Worker: Installed');
  // Skip waiting to activate immediately
  self.skipWaiting();
});

// Activate event - required for PWA
self.addEventListener('activate', (event) => {
  console.log('✅ Service Worker: Activated');
  // Claim clients immediately
  event.waitUntil(self.clients.claim());
});

// Fetch event - pass through to network (no caching)
self.addEventListener('fetch', (event) => {
  // Just let requests go through normally
  // No offline functionality - keeping it simple!
  event.respondWith(fetch(event.request));
});
