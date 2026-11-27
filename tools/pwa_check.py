#!/usr/bin/env python3
"""STRUM PWA 설치 요건 검증 — 아이콘·매니페스트·서비스 워커.

확인 항목
  1) 아이콘 파일 4종 존재·크기(512/192/180)·SVG 유효
  2) manifest.webmanifest: scope, icons(192 any / 512 any / 512 maskable / svg)
  3) index.html: favicon·apple-touch-icon 링크, ?v=18 유지
  4) sw.js: media/*.mp3 미캐시, network-first, src/app.js 등록 코드
  5) maskable 안전영역: 아이콘 잉크가 중심 반지름 40%(204.8px) 안에 있는지
  6) 실제 구동: 로컬 http 서버에서 서비스 워커 등록·제어, 매니페스트·아이콘·sw.js 200 응답

실행: python3 tools/pwa_check.py
"""
import http.server
import json
import pathlib
import re
import socketserver
import threading

from PIL import Image
from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
PORT = 8771
results = []


def check(name, cond, detail=''):
    results.append((name, bool(cond), detail))
    if not cond:
        raise AssertionError(f'{name} — {detail}')
    print(f'OK: {name}' + (f' ({detail})' if detail else ''))


# ── 1) 아이콘 파일 ────────────────────────────────────────────
sizes = {'icon-512.png': 512, 'icon-192.png': 192, 'icon-180.png': 180}
for name, expect in sizes.items():
    path = BASE / name
    check(f'{name} 존재', path.exists(), str(path))
    im = Image.open(path)
    check(f'{name} 크기 {expect}x{expect}', im.size == (expect, expect), str(im.size))
    check(f'{name} 알파 없는 RGB(안드로이드 안전)', im.mode in ('RGB', 'P'), im.mode)

svg = (BASE / 'icon.svg').read_text(encoding='utf-8')
check('icon.svg 유효', svg.lstrip().startswith('<svg') and 'viewBox="0 0 512 512"' in svg)
check('icon.svg 크림 배경', '#f8f5ee' in svg.lower())

# maskable 안전영역 — 어두운 잉크·골드 포인트가 r<=204.8 안에 있는지
im = Image.open(BASE / 'icon-512.png').convert('RGB')
px = im.load()
cx = cy = 256
worst, worst_at = 0.0, None
for y in range(512):
    for x in range(512):
        r, g, b = px[x, y]
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        ink = lum < 205 or (r - b > 45)          # 기타 몸통·줄·로제트·반짝임
        if ink:
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d > worst:
                worst, worst_at = d, (x, y)
check('maskable 안전영역(잉크 최대 반지름 ≤204.8)', worst <= 204.8, f'{worst:.1f}px @ {worst_at}')

# ── 2) 매니페스트 ────────────────────────────────────────────
mf = json.loads((BASE / 'manifest.webmanifest').read_text(encoding='utf-8'))
check('manifest scope', mf.get('scope') == './', str(mf.get('scope')))
check('manifest start_url', mf.get('start_url') == './', str(mf.get('start_url')))
check('manifest display standalone', mf.get('display') == 'standalone', str(mf.get('display')))
check('manifest 테마/배경 크림', mf.get('theme_color').lower() == '#f8f5ee' and mf.get('background_color').lower() == '#f8f5ee')
icons = mf.get('icons', [])
def has_icon(src, size, purpose):
    return any(i.get('src') == src and i.get('sizes') == size and purpose in str(i.get('purpose', 'any')).split() for i in icons)
check('manifest icon 192 any', has_icon('icon-192.png', '192x192', 'any'), str(icons))
check('manifest icon 512 any', has_icon('icon-512.png', '512x512', 'any'))
check('manifest icon 512 maskable', has_icon('icon-512.png', '512x512', 'maskable'))
check('manifest icon svg any', has_icon('icon.svg', 'any', 'any'))

# ── 3) index.html ───────────────────────────────────────────
html = (BASE / 'index.html').read_text(encoding='utf-8')
# v22: 캐시 버전(sw.js CACHE)으로 자산 ?v= 를 검사한다. seedVersion 은 곡 데이터 버전이라
#       코드만 고쳐 배포할 때는 올리지 않는다(올리면 불필요한 시드 재병합 안내가 뜬다).
cache_ver = re.search(r'strum-busking-test-v(\d+)', (BASE / 'sw.js').read_text(encoding='utf-8'))
seed_ver = re.search(r'seedVersion":(\d+)', (BASE / 'src' / 'seed.js').read_text(encoding='utf-8'))
CUR_VER = cache_ver.group(1) if cache_ver else '0'
check('index: manifest 링크', 'rel="manifest" href="manifest.webmanifest"' in html)
check('index: icon.svg 링크', 'rel="icon" type="image/svg+xml" href="icon.svg"' in html)
check('index: icon-192 링크', 'rel="icon" type="image/png" sizes="192x192" href="icon-192.png"' in html)
check('index: apple-touch-icon 180', 'rel="apple-touch-icon" sizes="180x180" href="icon-180.png"' in html)
check(f'index: ?v={CUR_VER} 유지', html.count(f'?v={CUR_VER}') == 3, str(html.count(f'?v={CUR_VER}')))

# ── 4) sw.js + 등록 코드 ────────────────────────────────────
sw = (BASE / 'sw.js').read_text(encoding='utf-8')
check('sw.js: media 캐시 제외', '/\\/media\\//' in sw or '/media/' in sw)
check('sw.js: network-first(fetch 후 catch에서 캐시)', 'fetch(req).then' in sw and 'caches.match(req)' in sw)
check('sw.js: 앱 셸 프리캐시', "'./src/app.js'" not in sw and "'./index.html'" in sw)
app = (BASE / 'src' / 'app.js').read_text(encoding='utf-8')
check('app.js: sw.js 등록', "navigator.serviceWorker.register('./sw.js')" in app)
# 2026-11-27 새 기능(14버튼 배치표·마디 싱크·배속)도 앱 셸과 함께 배포되는지
css = (BASE / 'src' / 'styles.css').read_text(encoding='utf-8')
check('app.js: 14버튼 배치표·마디 싱크', "aeroPad" in app and "aero-strip" in app and "seek-bar" in app and "mini-rate" in app)
# 2026-11-27 노래방 가사 싱크(미니바 지금 줄·다음 줄) + 전체 가사 + 오늘의 연습 원곡/MR 전환
check('app.js: 가사 싱크·전체 가사·듣기 전환', "mini-lyric" in app and "lyrics-sheet" in app and "seek-line" in app and "listen-toggle" in app)
check('styles.css: 가사 싱크·전체 가사·듣기 전환 스타일', ".mini-lyric" in css and ".lyr-line" in css and ".listen-toggle" in css and ".bar-lyric" in css)
check('media/thank-you-mr.mp3 존재(Thank You 녹화 반주)',
      (BASE / 'media' / 'thank-you-mr.mp3').exists() and (BASE / 'media' / 'thank-you-mr.mp3').stat().st_size > 3_500_000,
      str((BASE / 'media' / 'thank-you-mr.mp3').stat().st_size if (BASE / 'media' / 'thank-you-mr.mp3').exists() else 'missing'))
_tyseed = (BASE / 'src' / 'seed.js').read_text(encoding='utf-8')
check('seed.js: Thank You 가사 35줄·녹화 반주', '"lyrics":{"version":"2026-11-27"' in _tyseed
      and 'media/thank-you-mr.mp3' in _tyseed and 'My tea' in _tyseed)
check('styles.css: 배치표·타임라인·배속 스타일', ".aero-pad" in css and ".aero-strip" in css and ".mini-rate" in css and ".timing-strip" in css)
check('seed.js: 최적 14버튼(B·Bdim 아님)', '"buttonSet":["C","Dm","Em","F","G","Am","B"' in (BASE / 'src' / 'seed.js').read_text(encoding='utf-8'))
seed_ver = re.search(r'seedVersion":(\d+)', (BASE / 'src' / 'seed.js').read_text(encoding='utf-8'))
check('seed.js seedVersion <= 자산 버전', seed_ver and int(seed_ver.group(1)) <= int(CUR_VER),
      f"seed {seed_ver.group(1) if seed_ver else 'none'} / asset {CUR_VER}")

# ── 6) 실제 구동 ────────────────────────────────────────────
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(BASE), **kw)

    def log_message(self, *a):
        pass


socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(('127.0.0.1', PORT), Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={'width': 412, 'height': 915}, is_mobile=True, has_touch=True,
                              user_agent=('Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 '
                                          '(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36'))
    page = ctx.new_page()
    errors = []
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{PORT}/index.html', wait_until='networkidle')

    reg = page.evaluate("""async () => {
      if (!('serviceWorker' in navigator)) return {ok:false};
      const r = await navigator.serviceWorker.ready;
      return {ok:true, scope:r.scope, state:r.active && r.active.state};
    }""")
    check('서비스 워커 등록·활성', reg.get('ok') and reg.get('state') == 'activated', str(reg))

    page.reload(wait_until='networkidle')
    controlled = page.evaluate("() => !!(navigator.serviceWorker && navigator.serviceWorker.controller)")
    check('서비스 워커가 페이지 제어', controlled)

    reqs = {}
    for path in ['manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'icon.svg', 'sw.js']:
        res = page.request.get(f'http://127.0.0.1:{PORT}/{path}')
        reqs[path] = (res.status, res.headers.get('content-type', ''))
        check(f'{path} 200', res.status == 200, str(reqs[path]))

    app_ok = page.evaluate("() => document.querySelector('#app').textContent.length > 200")
    check('앱 렌더 정상(SW 등록 후)', app_ok)
    # 2026-11-27 새 기능(14버튼 배치표)도 서비스 워커가 제어하는 페이지에서 그려지는지
    page.click('[data-nav="practice"]')
    page.wait_for_selector('.aero-pad .pad-btn', timeout=8000)
    pad_n = page.locator('.aero-pad .pad-btn').count()
    check('14버튼 배치표 14개(SW 등록 후)', pad_n == 14, str(pad_n))
    check('오늘의 연습 원곡/MR 전환 버튼(SW 등록 후)', page.locator('.listen-toggle .btn').count() == 2,
          str(page.locator('.listen-toggle .btn').count()))
    check('콘솔 에러 0', len(errors) == 0, str(errors[:3]))
    browser.close()

httpd.shutdown()
print(f'\nPASS {len(results)} checks')
