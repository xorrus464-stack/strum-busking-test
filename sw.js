/* STRUM — 홈 화면에 추가 / 앱 설치(PWA)용 최소 서비스 워커
   · 네트워크 우선: 새로 배포한 index.html·src/seed.js·src/app.js·src/styles.css 가
     항상 먼저 보이고, 오프라인일 때만 캐시를 씁니다.
   · 반주 음원(media/*.mp3)과 범위 요청(Range)은 손대지 않고 그대로 통과시킵니다. */
var CACHE = 'strum-busking-test-v28';
var SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon.svg',
  './icon-192.png',
  './icon-180.png',
  './icon-512.png',
  /* v23→v24: 코드 운지표(SVG)까지 새 앱 셸로 받는다 */
  './src/pitch-grain.js',
  './src/pitch-worklet.js'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE)
      .then(function (cache) { return cache.addAll(SHELL).catch(function () { }); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.map(function (key) {
          return key === CACHE ? null : caches.delete(key);
        }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.method !== 'GET') return;

  var url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;          /* 유튜브·폰트 등 외부 요청은 그대로 */
  if (/\/media\//.test(url.pathname)) return;               /* 반주 음원은 캐시하지 않음 */
  if (req.headers.has('range')) return;                     /* 오디오 구간 요청은 그대로 */

  event.respondWith(
    fetch(req).then(function (res) {
      if (res && res.ok && res.type === 'basic') {
        var copy = res.clone();
        caches.open(CACHE).then(function (cache) { cache.put(req, copy); }).catch(function () { });
      }
      return res;
    }).catch(function () {
      return caches.match(req).then(function (hit) {
        if (hit) return hit;
        if (req.mode === 'navigate') return caches.match('./index.html');
        return Response.error();
      });
    })
  );
});
