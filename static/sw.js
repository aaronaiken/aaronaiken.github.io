const CACHE_NAME = 'status-app-v1';
const ASSETS = [
  '/publish',
  '/static/apple-touch-icon.png' // Add your icon path here
  '/static/sw.js',
  '/static/manifest.json'
];

// Install: Save the form to the phone's cache
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
});

// Fetch: Serve the cached form immediately
self.addEventListener('fetch', (event) => {
  // Only cache GET requests (the form), let POST (the update) go to the network
  if (event.request.method === 'GET') {
    event.respondWith(
      caches.match(event.request).then((response) => {
        return response || fetch(event.request);
      })
    );
  }
});