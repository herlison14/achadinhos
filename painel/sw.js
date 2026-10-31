/* Service worker do painel: deixa o painel instalável e abre mesmo sem internet com os últimos dados vistos.
   Regras de segurança: só atende GET do mesmo site (nunca o Worker de cliques/ganhos, que usa chave e código 2FA)
   e nunca guarda nada além do próprio painel e dos JSON públicos em /dados/. */
var V = 'painel-v1';
var SHELL = ['./', 'index.html', 'manifest.webmanifest', 'icone-192.png', 'icone-512.png'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(V).then(function (c) { return c.addAll(SHELL); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== V; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (e) {
  var r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== self.location.origin) return;
  if (!(u.pathname.indexOf('/painel/') === 0 || u.pathname.indexOf('/dados/') === 0)) return;
  // rede primeiro (dados sempre frescos); se cair a conexão, usa a última cópia
  e.respondWith(fetch(r).then(function (res) {
    if (res && res.ok) { var cp = res.clone(); caches.open(V).then(function (c) { c.put(r, cp); }); }
    return res;
  }).catch(function () {
    return caches.match(r).then(function (m) { return m || (r.mode === 'navigate' ? caches.match('./') : Response.error()); });
  }));
});
