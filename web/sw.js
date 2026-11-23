// Manevi Bahçem PWA: sayfa iskeleti önbellekte; veriler önce ağdan (her açılışta güncel), ağ yoksa son kopya.
const SURUM = "mb-v1";
const ISKELET = ["./", "index.html", "logo.webp", "ikon-192.png", "ikon-512.png", "manifest.webmanifest"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SURUM).then(c => c.addAll(ISKELET)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(adlar => Promise.all(adlar.filter(a => a !== SURUM).map(a => caches.delete(a))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  // Veri ve sayfa: önce ağ, olmazsa önbellek
  if (url.pathname.endsWith(".json") || e.request.mode === "navigate") {
    const anahtar = url.pathname.endsWith(".json") ? url.pathname : "index.html";
    e.respondWith(fetch(e.request).then(r => {
      if (r.ok) { const kopya = r.clone(); caches.open(SURUM).then(c => c.put(anahtar, kopya)); }
      return r;
    }).catch(() => caches.match(anahtar)));
    return;
  }
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
