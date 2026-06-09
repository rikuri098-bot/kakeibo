// 家計簿アプリ Service Worker（最低限のオフライン対応）
const CACHE = "kakeibo-v1";
const ASSETS = ["/", "/static/index.html", "/static/icon-192.png", "/static/icon-512.png", "/manifest.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // API・認証はネットワークに任せる（キャッシュしない）
  if (/^\/(api|login|logout|register)/.test(url.pathname)) return;
  // それ以外はネットワーク優先・失敗時キャッシュ（最低限のオフライン）
  e.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(req).then((r) => r || caches.match("/")))
  );
});
