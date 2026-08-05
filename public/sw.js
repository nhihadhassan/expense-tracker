const CACHE_NAME = "expense-tracker-shell-v2";
const SHELL = ["/", "/manifest.webmanifest", "/favicon.svg"];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if(request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  const shellRequest = SHELL.includes(url.pathname);
  if(!shellRequest) return;
  event.respondWith(
    fetch(request).catch(() => caches.match(request).then(cached => cached || caches.match("/")))
  );
});
