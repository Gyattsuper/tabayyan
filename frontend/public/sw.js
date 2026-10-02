// Minimal service worker: makes the site installable as an app (needed for
// "share to Tabayyan" from WhatsApp on Android). It caches nothing, so results
// always come fresh from the server.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
