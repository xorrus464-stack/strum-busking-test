#!/usr/bin/env python3
"""STRUM 브라우저 검증 (PC + 갤럭시 모바일 에뮬레이션).

실행: python3 tools/e2e_check.py
임시 http.server 를 띄워 실제 페이지를 열고, 콘솔 에러·가로 넘침·핵심 화면을 확인한다.
스크린샷: docs/screenshots/*.png
"""
import http.server
import json
import os
import pathlib
import re
import socketserver
import threading

from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
SHOTS = BASE / 'docs' / 'screenshots'
SHOTS.mkdir(parents=True, exist_ok=True)
PORT = 8765
errors = []
results = []


class Handler(http.server.SimpleHTTPRequestHandler):
    """정적 파일 서버. GitHub Pages 처럼 Range 요청(206)을 지원해 오디오 '마디 이동'을 실제로 검증한다."""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(BASE), **kw)

    def log_message(self, *a):
        pass

    def do_GET(self):
        rng = self.headers.get('Range')
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().do_GET()
        m = re.match(r'bytes=(\d*)-(\d*)$', rng.strip())
        if not m:
            return super().do_GET()
        size = os.path.getsize(path)
        start = int(m.group(1)) if m.group(1) else 0
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.end_headers()
            return
        with open(path, 'rb') as f:
            f.seek(start)
            chunk = f.read(end - start + 1)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(len(chunk)))
        self.end_headers()
        self.wfile.write(chunk)


def check(name, cond, detail=''):
    results.append((name, bool(cond), detail))
    if not cond:
        raise AssertionError(f'{name} — {detail}')


def overflow(page):
    return page.evaluate("() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")


def run(pw, name, viewport, mobile=False):
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport=viewport, device_scale_factor=2 if mobile else 1,
                              is_mobile=mobile, has_touch=mobile,
                              user_agent=('Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 '
                                          '(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36') if mobile else None)
    page = ctx.new_page()
    page.on('console', lambda m: errors.append(f'[{name}] console.{m.type}: {m.text}')
            if m.type == 'error' and 'compute-pressure' not in m.text else None)
    page.on('pageerror', lambda e: errors.append(f'[{name}] pageerror: {e}'))
    page.goto(f'http://127.0.0.1:{PORT}/index.html', wait_until='networkidle')

    check(f'{name}: 홈 렌더', 'STRUM' in page.content() and '남자키 원터치 악보' in page.content())
    o = overflow(page)
    check(f'{name}: 홈 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))

    # 곡 라이브러리
    page.click('[data-nav="songs"]')
    page.wait_for_selector('#song-list')
    page.select_option('#song-filter', 'chart-ready')
    rows = page.locator('.song-row').count()
    check(f'{name}: 악보 완료 필터', rows >= 100, f'{rows} rows')
    check(f'{name}: 남자키 배지', page.locator('.tag.chart-tag').count() >= 100)
    page.select_option('#song-filter', 'reference')
    refs = page.locator('.song-row').count()
    check(f'{name}: 비음악·참고 필터', refs >= 30, f'{refs}')
    page.select_option('#song-filter', 'original')
    org = page.locator('.song-row').count()
    check(f'{name}: 자작·AI곡 필터', org >= 1, f'{org}')
    page.select_option('#song-filter', 'chart-pending')
    pend = page.locator('.song-row').count()
    check(f'{name}: 검수 대기 필터', pend == 0, f'{pend}')  # 2026-11-22 음원 분석으로 9곡 모두 부분 확인으로 이동
    page.select_option('#song-filter', 'all')
    page.fill('#song-search', '신호등')
    page.wait_for_timeout(200)
    check(f'{name}: 곡명 검색(신호등)', page.locator('.song-row').count() >= 1)
    page.fill('#song-search', '')
    page.select_option('#song-filter', 'chart-ready')
    o = overflow(page)
    check(f'{name}: 곡 목록 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))

    # 원터치 컬러 악보
    page.locator('.song-row', has_text='Way Back Home').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    html = page.content()
    for token in ['Capo +3', 'G폼', 'ONE-TOUCH', 'bar-cells', 'stroke-strip']:
        check(f'{name}: 악보 {token}', token in html)
    colors = page.evaluate("""() => [...document.querySelectorAll('.cc')].map(e => getComputedStyle(e).backgroundColor)""")
    uniq = sorted(set(colors))
    check(f'{name}: 마디 카드 색상 4종 이상', len(uniq) >= 4, str(uniq))
    o = overflow(page)
    check(f'{name}: 악보 모달 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'chart-{name}.png'))

    # 14버튼 완주 곡: 손으로 잡을 코드가 없다
    check(f'{name}: 완주 곡 손 코드 없음 안내', '손으로 잡을 코드 없음' in page.content())
    page.click('button:has-text("SimplifyChord")')
    check(f'{name}: 완주 곡 손 코드 0개', '손으로 잡는 코드' in page.content() and page.locator('.dex-card').count() == 0)
    page.click('button:has-text("스트로크·퍼커시브")')
    check(f'{name}: 퍼커시브 단계', '4단계로 만드는 퍼커시브' in page.content())
    page.click('button:has-text("근거")')
    check(f'{name}: 근거 링크', page.locator('ul.ev a').count() >= 2)
    page.click('[data-act="close"]')

    # 손 코드(슬롯)가 있는 곡 — 희재: 카포 +4에서 D가 B♭ 모양(1프렛 바레)
    page.locator('.song-row', has_text='희재').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    check(f'{name}: 손 코드 운지표 카드', page.locator('.dex-card').count() == 1, str(page.locator('.dex-card').count()))
    check(f'{name}: 코드 다이어그램(점·바레·뮤트)', page.locator('.fret-diagram .fd-dot').count() >= 2
          and page.locator('.fret-diagram .fd-barre').count() >= 1
          and page.locator('.fret-diagram .fd-mark').count() >= 1)
    code = page.locator('.dex-code').first.inner_text().strip()
    check(f'{name}: 운지 코드 x13331', code == 'x13331', code)
    fing = page.locator('.dex-fing').first.inner_text()
    check(f'{name}: 손가락 번호 안내', '1:5~1번줄 1프렛 바레' in fing and '2:4번줄3프렛' in fing, fing)
    check(f'{name}: 실제 코드 이름 표시', page.locator('.cc.is-slot .cc-btn').first.inner_text().strip() == 'D')
    check(f'{name}: 슬롯 기호(S1) 대신 모양 표시', 'B♭ 모양' in page.locator('.cc.is-slot').first.inner_text())
    dexbox = page.locator('.dex-card').first.bounding_box() or {}
    modalbox = page.locator('.chart-modal').bounding_box() or {}
    check(f'{name}: 운지 카드가 모달 안에 들어옴', (dexbox.get('x', 0) >= modalbox.get('x', 0) - 1)
          and (dexbox.get('x', 0) + dexbox.get('width', 0) <= modalbox.get('x', 0) + modalbox.get('width', 0) + 1),
          f'card={dexbox} modal={modalbox}')
    o = overflow(page)
    check(f'{name}: 운지표 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'chord-dex-{name}.png'))
    page.click('button:has-text("SimplifyChord")')
    page.wait_for_selector('.dex-card')
    check(f'{name}: SimplifyChord 탭 운지표', page.locator('.fret-diagram').count() >= 1
          and '에어로밴드에 넣는 방법' in page.content())
    check(f'{name}: 손 코드 읽는 법 안내', '실제로 울리는 코드' in page.content())
    page.screenshot(path=str(SHOTS / f'simplify-{name}.png'))
    page.click('[data-act="close"]')

    # 2026-11-22 새로 반영한 음원 분석 곡(추가 곡·자작 항목·긴 차트)
    page.select_option('#song-filter', 'all')
    page.fill('#song-search', '10,000 Hours')
    page.wait_for_timeout(200)
    page.locator('.song-row', has_text='10,000 Hours').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    html = page.content()
    check(f'{name}: 10,000 Hours 카포·악보', 'Capo +2' in html and 'bar-cells' in html)
    check(f'{name}: 10,000 Hours 별도 곡 안내', 'Dan + Shay' in html)
    check(f'{name}: 10,000 Hours 구간 경계(후렴 1 0:33–1:01)', '후렴 1 · 0:33–1:01' in html)
    page.click('[data-act="close"]')
    page.fill('#song-search', '어떤이별')
    page.wait_for_timeout(200)
    page.locator('.song-row', has_text='어떤이별').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    html = page.content()
    check(f'{name}: 어떤이별 후반 G 전조 구간', '후반 G 전조' in html)
    page.click('[data-act="close"]')
    page.fill('#song-search', '커피')
    page.wait_for_timeout(200)
    page.locator('.song-row', has_text='커피').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    html = page.content()
    check(f'{name}: 커피(자작 항목) 악보 표시', '음원 분석' in html and 'bar-cells' in html)
    page.click('[data-act="close"]')
    page.fill('#song-search', '될 대로 되라고 해')
    page.wait_for_timeout(200)
    page.locator('.song-row', has_text='될 대로').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    bars = page.locator('.cc').count()
    check(f'{name}: 긴 차트(124마디) 렌더', bars >= 100, f'{bars}')
    o = overflow(page)
    check(f'{name}: 긴 차트 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'chart-audio-{name}.png'))
    page.click('[data-act="close"]')
    page.fill('#song-search', '')
    page.wait_for_timeout(200)

    # 하단 미니 플레이어 · MR 버튼 (2026-11-22 v13)
    page.fill('#song-search', '희재')
    page.wait_for_timeout(250)
    page.locator('.song-row', has_text='희재').first.locator('button', has_text='음악').click()
    page.wait_for_selector('.mini-player iframe')
    src = page.locator('.mini-player iframe').get_attribute('src') or ''
    check(f'{name}: 미니 플레이어 임베드(자동재생)', 'youtube-nocookie.com/embed/' in src and 'autoplay=1' in src, src)
    fbox = page.locator('.mini-frame').bounding_box() or {}
    check(f'{name}: 미니 프레임 보이는 크기', (fbox.get('width') or 0) > 90 and (fbox.get('height') or 0) > 50, str(fbox))
    pad = page.evaluate("parseFloat(getComputedStyle(document.body).paddingBottom)||0")
    check(f'{name}: 하단 여백 확보', pad > 60, str(pad))
    # 로드맵
    page.click('[data-nav="roadmap"]')
    page.wait_for_timeout(200)
    check(f'{name}: 탭 이동 후 미니 플레이어 유지', page.locator('.mini-player').count() == 1)
    page.click('[data-nav="songs"]')
    page.fill('#song-search', '희재')
    page.wait_for_timeout(250)
    page.locator('.song-row', has_text='희재').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    check(f'{name}: 악보 화면에서도 유지', page.locator('.mini-player').count() == 1)
    page.locator('.chart-modal').locator('button', has_text='MR 듣기').click()
    page.wait_for_timeout(300)
    check(f'{name}: MR 버튼 → MR 모드', page.locator('.mini-badge').inner_text().strip() == 'MR')
    mr_src = page.locator('.mini-player iframe').get_attribute('src') or ''
    check(f'{name}: MR 영상 재생', 'nu3BNEd4u2o' in mr_src, mr_src)
    check(f'{name}: MR 재생 중 악보 유지', page.locator('.chart-modal').count() == 1)
    dock = page.locator('.mini-player').bounding_box() or {}
    mbox = page.locator('.chart-modal').bounding_box() or {}
    check(f'{name}: 악보가 미니 플레이어를 가리지 않음', (mbox.get('y', 0) + mbox.get('height', 0)) <= dock.get('y', 0) + 2,
          f"modal={mbox.get('y', 0) + mbox.get('height', 0):.0f} dock={dock.get('y', 0):.0f}")
    o = overflow(page)
    check(f'{name}: 미니 플레이어 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'mini-chart-{name}.png'))
    page.click('[data-act="close"]')
    # 2026-11-23 음악 항목 162개 전부 MR 연결 → 'MR 없음' 화면은 새로 등록한 곡으로 확인한다
    page.click('button:has-text("+ 새 곡 등록")')
    page.wait_for_selector('#song-form')
    page.fill('#song-form input[name="title"]', 'e2e MR 없는 곡')
    page.fill('#song-form input[name="artist"]', 'e2e')
    page.click('#song-form button[type="submit"]')
    page.wait_for_timeout(250)
    page.fill('#song-search', 'e2e MR 없는 곡')
    page.wait_for_timeout(250)
    page.locator('.song-row', has_text='e2e MR 없는 곡').first.locator('button', has_text='MR 없음').click()
    page.wait_for_selector('#mr-form')
    check(f'{name}: MR 없음 안내', 'MR이 아직 등록되지 않았습니다' in page.content())
    check(f'{name}: MR 검색 링크', 'youtube.com/results?search_query=' in (page.locator('#mr-form').evaluate("e => e.closest('.modal').innerHTML")))
    page.fill('#mr-form input[name="mrUrl"]', 'https://www.youtube.com/watch?v=IkF6QIQ0Q0A')
    page.click('#mr-form button[type="submit"]')
    page.wait_for_selector('.mini-badge')
    page.wait_for_timeout(200)
    st = json.loads(page.evaluate("() => localStorage.getItem('strum-busking-v2')"))
    edited = [x for x in st['songs'] if x['title'] == 'e2e MR 없는 곡'][0]
    check(f'{name}: 붙여넣은 MR 저장', edited.get('mrUrl', '').endswith('IkF6QIQ0Q0A') and edited.get('mrEdited') is True, str(edited.get('mrUrl')))
    check(f'{name}: 저장한 MR 미니 재생', page.locator('.mini-badge').inner_text().strip() == 'MR')
    w1 = (page.locator('.mini-frame').bounding_box() or {}).get('width', 0)
    page.click('[data-act="mini-collapse"]')
    page.wait_for_timeout(200)
    w2 = (page.locator('.mini-frame').bounding_box() or {}).get('width', 0)
    check(f'{name}: 접어도 프레임 유지(숨김 아님)', 60 < w2 < w1, f'{w1}->{w2}')
    page.click('[data-act="mini-close"]')
    page.wait_for_timeout(150)
    check(f'{name}: 닫기 동작', page.locator('.mini-player').count() == 0)
    pad = page.evaluate("parseFloat(getComputedStyle(document.body).paddingBottom)||0")
    check(f'{name}: 닫은 뒤 하단 여백 원복', pad == 0, str(pad))
    page.fill('#song-search', '')
    page.wait_for_timeout(200)

    # 2026-11-23 MR (seed v16): 「잠깐 시간 될까」 YouTube MR · 로꼬 「픽픽」 MR 음원 파일(주성 님 녹화)
    media = page.request.get(f'http://127.0.0.1:{PORT}/media/pikpik-mr.mp3')
    check(f'{name}: MR 음원 파일 서빙(media/pikpik-mr.mp3)',
          media.status == 200 and int(media.headers.get('content-length', 0)) > 1_000_000,
          f"{media.status} {media.headers.get('content-length')}")
    page.fill('#song-search', '잠깐 시간 될까')
    page.wait_for_timeout(250)
    page.locator('.song-row', has_text='잠깐 시간 될까').first.locator('button.mr-on').click()
    page.wait_for_selector('.mini-player iframe')
    src = page.locator('.mini-player iframe').first.get_attribute('src') or ''
    check(f'{name}: 잠깐 시간 될까 MR 재생', '_aJasCmlQC8' in src, src)
    check(f'{name}: 잠깐 시간 될까 MR 배지', page.locator('.mini-badge').inner_text().strip() == 'MR')
    page.click('[data-act="mini-close"]')
    page.fill('#song-search', '픽픽')
    page.wait_for_timeout(250)
    page.locator('.song-row', has_text='픽픽').first.locator('button.mr-on').click()
    page.wait_for_selector('.mini-player audio#mini-audio')
    a_src = page.locator('.mini-player audio#mini-audio').get_attribute('src') or ''
    check(f'{name}: 픽픽 MR 음원 파일 미니 재생', 'media/pikpik-mr.mp3' in a_src, a_src)
    check(f'{name}: MR 음원은 iframe 없이 <audio> 재생', page.locator('.mini-player iframe').count() == 0)
    page.wait_for_function("() => { const a = document.querySelector('#mini-audio'); return !!a && a.readyState >= 1 && a.duration > 60; }",
                           timeout=15000)
    dur = page.evaluate("() => document.querySelector('#mini-audio').duration")
    check(f'{name}: MR 음원 실제 로드(3분 10초)', 180 < dur < 200, str(dur))
    page.locator('.song-row', has_text='픽픽').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    check(f'{name}: MR 음원 재생 중 악보 유지', page.locator('.mini-player audio#mini-audio').count() == 1)
    o = overflow(page)
    check(f'{name}: MR 음원 미니 플레이어 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'mini-audio-mr-{name}.png'))
    page.click('[data-act="close"]')
    page.click('[data-act="mini-close"]')
    page.fill('#song-search', '')
    page.wait_for_timeout(200)

    # 2026-11-23 MR (seed v17): AI 보컬 제거 추출 MR 음원 2건 — jehoda · nanome 커피
    for fname, expect_sec, label in (('jehoda-mr.mp3', 235, '괜히 보고 싶은 사실'), ('coffee-mr.mp3', 182, '내 첫 자작곡'),
                                     ('toy-mr.mp3', 242, '나는 버려질 장난감'), ('weather-mr.mp3', 189, '날씨가 좋고 바람도 좋아'),
                                     # 2026-11-24 주성 님 녹화 → -5반음(남자키) MP3
                                     ('shannon-sabyeol-mr.mp3', 215, '死別'), ('choiyuri-saenggak-mr.mp3', 197, '생각을 멈추다 보면'),
                                     ('goodbye-bye-mr.mp3', 247, 'Good Bye-Bye'), ('kisum-seo-eoreun-mr.mp3', 168, '서, 어른')):
        head = page.request.get(f'http://127.0.0.1:{PORT}/media/{fname}')
        check(f'{name}: MR 음원 서빙(media/{fname})',
              head.status == 200 and int(head.headers.get('content-length', 0)) > 1_000_000,
              f"{head.status} {head.headers.get('content-length')}")
        page.fill('#song-search', label)
        page.wait_for_timeout(300)
        row = page.locator('.song-row', has_text=label).first
        row.locator('button.mr-on').click()
        page.wait_for_selector('.mini-player audio#mini-audio')
        src = page.locator('.mini-player audio#mini-audio').get_attribute('src') or ''
        check(f'{name}: {label} MR 음원 미니 재생', fname in src, src)
        check(f'{name}: {label} MR 음원은 <audio> 재생(iframe 없음)', page.locator('.mini-player iframe').count() == 0)
        page.wait_for_function(
            "() => { const a = document.querySelector('#mini-audio'); return !!a && a.readyState >= 1 && a.duration > 60; }",
            timeout=20000)
        dur = page.evaluate("() => document.querySelector('#mini-audio').duration")
        check(f'{name}: {label} MR 음원 길이 확인({expect_sec}초)', abs(dur - expect_sec) < 12, str(dur))
        played = page.evaluate(
            "() => { const a = document.querySelector('#mini-audio'); "
            "return a.play().then(() => new Promise(r => setTimeout(() => r({t: a.currentTime, p: a.paused}), 900))) "
            ".then(v => v).catch(e => ({err: String(e)})); }")
        check(f'{name}: {label} MR 음원 실제 재생(소리 진행)', not played.get('err') and not played.get('p') and played.get('t', 0) > 0, str(played))
        page.click('[data-act="mini-close"]')
        page.fill('#song-search', '')
        page.wait_for_timeout(150)

    # 2026-11-26 Good Bye-Bye: 음악(풀트랙)도 저장소 media/ 음원으로 재생 + 실시간 키 조절 + 악보 B♭ Capo +3
    head = page.request.get(f'http://127.0.0.1:{PORT}/media/goodbye-bye-full.mp3')
    check(f'{name}: 음악 음원 서빙(media/goodbye-bye-full.mp3)',
          head.status == 200 and int(head.headers.get('content-length', 0)) > 5_000_000,
          f"{head.status} {head.headers.get('content-length')}")
    page.fill('#song-search', 'Good Bye-Bye')
    page.wait_for_timeout(300)
    gb = page.locator('.song-row', has_text='Good Bye-Bye').first
    gb_txt = gb.inner_text()
    check(f'{name}: Good Bye-Bye 카드 키 표기(Bb · Capo +3)', 'Bb' in gb_txt and 'Capo +3' in gb_txt, gb_txt[:120])
    gb.locator('button', has_text='음악').click()
    page.wait_for_selector('.mini-player audio#mini-audio')
    f_src = page.locator('.mini-player audio#mini-audio').get_attribute('src') or ''
    check(f'{name}: Good Bye-Bye 음악 = 로컬 음원 <audio>', 'media/goodbye-bye-full.mp3' in f_src, f_src)
    check(f'{name}: Good Bye-Bye 음악 배지', page.locator('.mini-badge').inner_text().strip() == '음악')
    check(f'{name}: Good Bye-Bye 음악도 실시간 키 조절 표시', page.locator('#mini-key').count() == 1)
    page.wait_for_function(
        "() => { const a = document.querySelector('#mini-audio'); return !!a && a.readyState >= 1 && a.duration > 200; }",
        timeout=20000)
    furl = page.evaluate("() => document.querySelector('#mini-audio').duration")
    check(f'{name}: Good Bye-Bye 음악 길이 확인(247초)', abs(furl - 247) < 8, str(furl))
    page.click('[data-act="mini-shift:-1"]')
    page.wait_for_timeout(400)
    check(f'{name}: Good Bye-Bye 음악 -1키 표시', page.locator('#mini-key-label').inner_text().strip() == '-1키',
          page.locator('#mini-key-label').inner_text())
    page.click('[data-act="mini-close"]')
    page.fill('#song-search', 'Good Bye-Bye')
    page.wait_for_timeout(250)
    page.locator('.song-row', has_text='Good Bye-Bye').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    cm = page.locator('.chart-modal').inner_text()
    check(f'{name}: Good Bye-Bye 악보 C폼 · Capo +3', 'Capo +3' in cm and 'C폼' in cm, cm[:200])
    check(f'{name}: Good Bye-Bye 악보 원곡·남자키 Bb', ('B♭' in cm or 'Bb' in cm), cm[:200])
    check(f'{name}: Good Bye-Bye 슬롯 0 안내', '슬롯' not in cm or '손으로 잡을 코드 없음' in cm or '14버튼만으로' in cm, cm[:200])
    page.click('[data-act="close"]')
    page.fill('#song-search', '')
    page.wait_for_timeout(200)

    # ── 2026-11-27 최적 14버튼 배치 · 마디 색깔 싱크 · 마디 이동 · 배속 · 주법 연결 ──
    page.fill('#song-search', 'Good Bye-Bye')
    page.wait_for_timeout(300)
    page.locator('.song-row', has_text='Good Bye-Bye').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    pad = page.locator('.aero-pad .pad-btn')
    pad_txt = [x.strip() for x in pad.all_inner_texts()]
    check(f'{name}: 14버튼 배치표 14개', pad.count() == 14, str(pad.count()))
    check(f'{name}: 배치표 열 순서(C·D·E·F·G·A·B 두 줄)',
          pad_txt == ['C', 'Cm', 'Dm', 'D', 'Em', 'E', 'F', 'Fm', 'G', 'Gm', 'Am', 'A', 'B', 'Bm'], str(pad_txt))
    check(f'{name}: 같은 열은 같은 루트 코드',
          all(top[0] == bottom[0] for top, bottom in zip(pad_txt[0::2], pad_txt[1::2])), str(pad_txt))
    check(f'{name}: Bdim 빠짐(최적 배치)', 'Bdim' not in page.content())
    cols_color = page.evaluate("() => [...document.querySelectorAll('.aero-pad .pad-col')].map(c => getComputedStyle(c).getPropertyValue('--c').trim())")
    check(f'{name}: 7열 색 7가지', len(cols_color) == 7 and len(set(cols_color)) == 7, str(cols_color))
    same_col = page.evaluate("""() => [...document.querySelectorAll('.aero-pad .pad-col')].every(c => {
        const b = c.querySelectorAll('.pad-btn');
        return getComputedStyle(b[0]).backgroundColor === getComputedStyle(b[1]).backgroundColor; })""")
    check(f'{name}: 한 열 두 버튼 같은 색', same_col)
    bars = page.locator('#chart-bars .bar')
    check(f'{name}: 마디 28개', bars.count() == 28, str(bars.count()))
    check(f'{name}: 마디 시작 시각 표기', page.locator('#chart-bars .bar-time').count() == 28,
          str(page.locator('#chart-bars .bar-time').count()))
    check(f'{name}: 실측 타임라인', '마디 타임라인 · 실측' in page.locator('#chart-timing').inner_text(),
          page.locator('#chart-timing').inner_text()[:80])
    page.locator('.chart-modal').locator('button', has_text='MR 듣기').click()
    page.wait_for_selector('.mini-player audio#mini-audio')
    page.wait_for_function("() => { const a = document.querySelector('#mini-audio'); return !!a && a.readyState >= 1 && a.duration > 200; }", timeout=20000)
    check(f'{name}: 배속 버튼 4개', page.locator('.mini-rate .rate-btn').count() == 4,
          str(page.locator('.mini-rate .rate-btn').count()))
    page.click('.mini-rate .rate-btn[data-rate="0.5"]')
    page.wait_for_timeout(350)
    rate = page.evaluate("() => document.querySelector('#mini-audio').playbackRate")
    check(f'{name}: 0.5배속(음정 유지)', abs(rate - 0.5) < 0.01, str(rate))
    check(f'{name}: 배속 중 음정 보존 설정', page.evaluate("() => { const a=document.querySelector('#mini-audio'); return a.preservesPitch !== false; }"))
    page.click('.mini-rate .rate-btn[data-rate="0.7"]')
    page.wait_for_timeout(250)
    rate = page.evaluate("() => document.querySelector('#mini-audio').playbackRate")
    check(f'{name}: 0.7배속', abs(rate - 0.7) < 0.01, str(rate))
    page.click('.mini-rate .rate-btn[data-rate="1"]')
    page.wait_for_timeout(250)
    bars.nth(5).click()
    page.wait_for_timeout(900)
    t_now = page.evaluate("() => document.querySelector('#mini-audio').currentTime")
    check(f'{name}: 6마디 클릭 → 그 마디(14초대)부터 재생', 13.2 <= t_now <= 18.5, str(t_now))
    check(f'{name}: 재생 중 마디 하나만 빛남', page.locator('#chart-bars .bar.now').count() == 1,
          str(page.locator('#chart-bars .bar.now').count()))
    check(f'{name}: 그 코드 버튼도 빛남(배치표)', page.locator('.aero-pad .pad-btn.now').count() == 1,
          str(page.locator('.aero-pad .pad-btn.now').count()))
    check(f'{name}: 악보 위 14버튼 바', page.locator('#aero-strip .pad-btn').count() == 14,
          str(page.locator('#aero-strip .pad-btn').count()))
    check(f'{name}: 위 14버튼 바에서도 같은 버튼이 빛남', page.locator('#aero-strip .pad-btn.now').count() == 1,
          str(page.locator('#aero-strip .pad-btn.now').count()))
    now_label = page.locator('#chart-now-label').inner_text()
    check(f'{name}: 지금 마디 표시', '마디' in now_label and '재생 중' in now_label, now_label)
    o = overflow(page)
    check(f'{name}: 악보(14버튼·타임라인) 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'chart-sync-{name}.png'))
    page.click('[data-act="mini-close"]')
    page.click('[data-act="close"]')
    # 유튜브 MR 곡: 추정 타임라인 + 오차 안내 배지
    page.fill('#song-search', '희재')
    page.wait_for_timeout(300)
    page.locator('.song-row', has_text='희재').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    cm_yt = page.locator('.chart-modal').inner_text()
    check(f'{name}: 유튜브 MR 추정 안내 배지', '유튜브 MR은 전주' in cm_yt and '녹화 음원' in cm_yt, cm_yt[:160])
    check(f'{name}: 추정 타임라인 표기', '추정' in page.locator('#chart-timing').inner_text())
    page.click('[data-act="close"]')
    # stage 1 곡: 오른손 주법 강좌 자동 연결
    page.fill('#song-search', 'Thank You')
    page.wait_for_timeout(300)
    page.locator('.song-row', has_text='Thank You').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    check(f'{name}: stage1 주법 배우기 버튼', page.locator('.lesson-link button', has_text='이 곡 오른손 주법 배우기').count() == 1)
    check(f'{name}: stage1 주법 이름(8비트)', '8비트 기본 스트로크' in page.locator('.lesson-link').inner_text(),
          page.locator('.lesson-link').inner_text()[:80])
    page.locator('.lesson-link button', has_text='이 곡 오른손 주법 배우기').click()
    page.wait_for_selector('.mini-player iframe', timeout=20000)
    l_src = page.locator('.mini-player iframe').first.get_attribute('src') or ''
    check(f'{name}: 주법 강좌 영상 연결(xP4IkqOP1yE)', 'xP4IkqOP1yE' in l_src, l_src[:90])
    check(f'{name}: 주법 강좌 배지', '강좌' in page.locator('.mini-player .mini-badge').first.inner_text())
    page.click('.mini-rate .rate-btn[data-rate="0.7"]')
    page.wait_for_timeout(300)
    check(f'{name}: YouTube 배속 0.7→0.75 안내', '0.75x' in page.locator('#mini-rate-live').inner_text(),
          page.locator('#mini-rate-live').inner_text())
    page.click('.mini-rate .rate-btn[data-rate="1"]')
    page.click('[data-act="mini-close"]')
    page.click('[data-act="close"]')
    # 2026-11-27 Thank You 녹화 반주 — 전곡 56마디 악보 · 노래방 가사 싱크 · 오늘의 연습 보컬/MR 전환
    page.fill('#song-search', 'Thank You')
    page.wait_for_timeout(300)
    page.locator('.song-row', has_text='Thank You').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    bars_ty = page.locator('#chart-bars .bar')
    check(f'{name}: Thank You 전곡 56마디', bars_ty.count() == 56, str(bars_ty.count()))
    check(f'{name}: Thank You 마디 시각 56개', page.locator('#chart-bars .bar-time').count() == 56,
          str(page.locator('#chart-bars .bar-time').count()))
    check(f'{name}: 녹화 실측 타임라인 표기', '마디 타임라인 · 실측' in page.locator('#chart-timing').inner_text())
    check(f'{name}: 가사 싱크 안내 문구', '지금 줄·다음 줄' in page.locator('#chart-timing').inner_text(),
          page.locator('#chart-timing').inner_text()[:100])
    check(f'{name}: 마디 카드에 가사 35줄', page.locator('#chart-bars .bar-lyric').count() == 35,
          str(page.locator('#chart-bars .bar-lyric').count()))
    check(f'{name}: 전체 가사 탭', page.locator('.subtabs button', has_text='전체 가사').count() == 1)
    page.locator('.subtabs button', has_text='전체 가사').click()
    page.wait_for_timeout(200)
    check(f'{name}: 전체 가사 35줄', page.locator('.lyr-line').count() == 35, str(page.locator('.lyr-line').count()))
    check(f'{name}: 가사 첫 줄(1절 My tea\'s gone cold)', "My tea's gone cold" in page.locator('.lyr-line').first.inner_text(),
          page.locator('.lyr-line').first.inner_text())
    check(f'{name}: 가사 구간 6개(1·2절·후렴1·3절·후렴2·3)', page.locator('.lyr-sec').count() == 6,
          str(page.locator('.lyr-sec').count()))
    # 9번째 줄(2절 첫 줄, 11마디=30.04초) — 누르면 그 줄부터 반주가 재생되고 미니바 가사도 바뀐다
    page.locator('.lyr-line').nth(8).click()
    page.wait_for_selector('.mini-player audio#mini-audio')
    check(f'{name}: Thank You 반주 음원 연결', 'thank-you-mr.mp3' in (page.locator('#mini-audio').get_attribute('src') or ''),
          page.locator('#mini-audio').get_attribute('src') or '')
    page.wait_for_function("() => { const a=document.querySelector('#mini-audio'); return !!a && a.readyState>=1 && a.duration>150; }",
                           timeout=20000)
    page.wait_for_timeout(1200)
    t_now = page.evaluate("() => document.querySelector('#mini-audio').currentTime")
    check(f'{name}: 가사 줄 클릭 → 30초대 이동', 29.5 <= t_now <= 36.5, str(t_now))
    ly_now = page.locator('#mini-lyric-now').inner_text()
    check(f'{name}: 미니바 현재 가사(2절 첫 줄)', ly_now.startswith('I drank too much'), ly_now)
    check(f'{name}: 미니바 다음 가사 미리보기', 'My head just feels in pain' in page.locator('#mini-lyric-next').inner_text(),
          page.locator('#mini-lyric-next').inner_text())
    check(f'{name}: 가사 목록 현재 줄 표시', page.evaluate("[...document.querySelectorAll('.lyr-line')].findIndex(e=>e.classList.contains('on'))") == 8)
    # 악보에서 후렴 21마디(60.04초)를 누르면 반주·가사가 함께 그 마디로
    page.locator('.subtabs button', has_text='원터치 악보').click()
    page.wait_for_timeout(200)
    bars_ty.nth(20).click()
    page.wait_for_timeout(1200)
    t_now = page.evaluate("() => document.querySelector('#mini-audio').currentTime")
    check(f'{name}: 21마디 클릭 → 60초대 재생', 59.5 <= t_now <= 67, str(t_now))
    ly_now = page.locator('#mini-lyric-now').inner_text()
    check(f'{name}: 마디 클릭 시 미니바 가사도 후렴으로', ly_now == 'And I want to thank you', ly_now)
    check(f'{name}: 지금 마디 = 21마디', page.evaluate("[...document.querySelectorAll('#chart-bars .bar')].findIndex(e=>e.classList.contains('now'))") == 20)
    check(f'{name}: 미니바 가사 태그(후렴 1)', '후렴 1' in page.locator('#mini-lyric-tag').inner_text(), page.locator('#mini-lyric-tag').inner_text())
    o = overflow(page)
    check(f'{name}: 가사·미니바 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'thank-you-lyrics-{name}.png'))
    page.click('[data-act="mini-close"]')
    page.click('[data-act="close"]')
    # 오늘의 연습 — 원곡(보컬) / MR 전환 버튼
    page.click('[data-nav="week"]')
    page.wait_for_selector('#week-goal-select')
    page.select_option('#week-goal-select', 'verified-003')
    page.wait_for_timeout(300)
    page.click('[data-nav="practice"]')
    page.wait_for_selector('.listen-toggle .btn', timeout=8000)
    labels = [x.strip() for x in page.locator('.listen-toggle .btn').all_inner_texts()]
    check(f'{name}: 오늘의 연습 원곡/MR 전환 버튼', len(labels) == 2 and '원곡' in labels[0] and 'MR' in labels[1], str(labels))
    check(f'{name}: 오늘의 목표곡 = Thank You', 'Thank You' in page.locator('.today-step').first.inner_text())
    page.locator('.listen-toggle .btn', has_text='MR').click()
    page.wait_for_selector('.mini-player audio#mini-audio')
    check(f'{name}: 오늘의 연습 MR 재생(녹화 반주)', 'thank-you-mr.mp3' in (page.locator('#mini-audio').get_attribute('src') or ''))
    check(f'{name}: MR 버튼 활성 표시', page.locator('.listen-toggle .btn.primary', has_text='MR').count() == 1)
    check(f'{name}: 오늘의 연습 가사 표시', 'And I want to thank you' in page.locator('#mini-lyric-now').inner_text()
          or 'My tea' in page.locator('#mini-lyric-now').inner_text(), page.locator('#mini-lyric-now').inner_text())
    page.locator('.listen-toggle .btn', has_text='원곡').click()
    page.wait_for_timeout(700)
    check(f'{name}: 원곡(보컬) 전환 → YouTube 음악 재생', page.locator('.mini-player .mini-badge').first.inner_text().strip() == '음악',
          page.locator('.mini-player .mini-badge').first.inner_text())
    check(f'{name}: 원곡 버튼 활성 표시', page.locator('.listen-toggle .btn.primary', has_text='원곡').count() == 1)
    o = overflow(page)
    check(f'{name}: 오늘의 연습 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'today-listen-{name}.png'))
    page.click('[data-act="mini-close"]')
    page.click('[data-nav="songs"]')
    page.wait_for_selector('#song-search')
    # YouTube 경로(IFrame API → seekTo·setPlaybackRate) — 테스트 더블로 호출을 실제로 확인한다.
    page.evaluate("""() => {
      window.__yt = {calls: [], t: 0, rate: 1, player: null};
      window.YT = { Player: function (node, cfg) {
        const self = this; window.__yt.player = self;
        self.getCurrentTime = () => window.__yt.t;
        self.getPlayerState = () => 1;
        self.seekTo = (s, allow) => { window.__yt.calls.push(['seek', s, allow]); window.__yt.t = s; };
        self.playVideo = () => window.__yt.calls.push(['play']);
        self.setPlaybackRate = r => { window.__yt.calls.push(['rate', r]); window.__yt.rate = r; };
        self.getPlaybackRate = () => window.__yt.rate;
        setTimeout(() => cfg.events && cfg.events.onReady && cfg.events.onReady({target: self}), 60);
      }};
    }""")
    page.fill('#song-search', '희재')
    page.wait_for_timeout(300)
    page.locator('.song-row', has_text='희재').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    yt_bars = page.locator('#chart-bars .bar')
    yt_bar2 = page.evaluate("() => Number(document.querySelectorAll('#chart-bars .bar')[7].dataset.bar)")
    page.locator('.chart-modal').locator('button', has_text='MR 듣기').click()
    page.wait_for_timeout(600)
    yt_bars.nth(7).click()
    page.wait_for_timeout(500)
    calls = page.evaluate("() => window.__yt.calls")
    seeks = [c for c in calls if c[0] == 'seek']
    expect_sec = float(page.evaluate("() => { const t = window.STRUM_SEED.songs.find(s => s.id === 'verified-006').chart.timing; return t.barTimes[7][0]; }"))
    check(f'{name}: YouTube 마디 클릭 → seekTo(마디 시작, 즉시)', bool(seeks) and abs(seeks[-1][1] - expect_sec) < 0.2 and seeks[-1][2] is True,
          f'{seeks[-1] if seeks else None} vs {expect_sec}')
    page.click('.mini-rate .rate-btn[data-rate="0.7"]')
    page.wait_for_timeout(300)
    calls = page.evaluate("() => window.__yt.calls")
    rates = [c[1] for c in calls if c[0] == 'rate']
    check(f'{name}: YouTube 배속 0.7 → setPlaybackRate(0.75)', 0.75 in rates, str(rates))
    page.evaluate("() => { window.__yt.t = 40; }")
    page.wait_for_timeout(700)
    check(f'{name}: YouTube 재생 위치가 마디 표시에 반영', '마디' in page.locator('#chart-now-label').inner_text(),
          page.locator('#chart-now-label').inner_text())
    page.click('[data-act="mini-close"]')
    page.click('[data-act="close"]')
    page.evaluate("() => { delete window.YT; window.__yt = null; }")
    page.fill('#song-search', '')
    page.wait_for_timeout(200)

    page.click('[data-nav="roadmap"]')
    body = page.content()
    for n in (1, 2, 3, 4):
        check(f'{name}: STAGE {n}', f'STAGE {n}' in body)
    chips = page.locator('.song-chip').count()
    check(f'{name}: 단계별 곡 칩', chips >= 15, f'{chips}')
    o = overflow(page)
    check(f'{name}: 로드맵 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'roadmap-{name}.png'), full_page=not mobile)

    # 주간 연습(DAY 1~7) + 오른손 주법 강좌
    page.click('[data-nav="week"]')
    body = page.content()
    for n in range(1, 8):
        check(f'{name}: 주간 연습 DAY {n}', f'DAY {n}' in body)
    check(f'{name}: 목표곡 추천 3개', page.locator('.week-rec').count() == 3, str(page.locator('.week-rec').count()))
    check(f'{name}: 주법 강좌 9개', page.locator('.lesson-card').count() == 9, str(page.locator('.lesson-card').count()))
    check(f'{name}: 강좌 YouTube 링크', page.locator('.lesson-card a[href*="youtube.com/watch?v="]').count() >= 10,
          str(page.locator('.lesson-card a[href*="youtube.com/watch?v="]').count()))
    check(f'{name}: 주간 진행률 0/7', '/ 7일' in page.content(), 'progress')
    page.select_option('#week-goal-select', 'verified-002')
    page.wait_for_timeout(300)
    check(f'{name}: 목표곡 변경(민들레)', '이번 주 목표곡' in page.content() and '민들레' in page.content(), 'goal')
    page.locator('input[data-week="1"]').check()
    page.wait_for_timeout(300)
    st = json.loads(page.evaluate("() => localStorage.getItem('strum-busking-v2')"))
    check(f'{name}: 1일차 체크 저장', bool(st.get('weekPlan', {}).get('days', {}).get('1')), str(st.get('weekPlan')))
    page.reload(wait_until='networkidle')
    page.click('[data-nav="week"]')
    check(f'{name}: 새로고침 후 체크 유지', page.locator('input[data-week="1"]').is_checked())
    page.locator('.lesson-card button', has_text='사이트에서 재생').first.click()
    page.wait_for_selector('.mini-player iframe')
    v_src = page.locator('.mini-player iframe').first.get_attribute('src') or ''
    check(f'{name}: 주법 강좌 미니 플레이어 재생', 'youtube-nocookie.com/embed/YVBDvDvvrdg' in v_src, v_src)
    check(f'{name}: 주법 강좌 배지', '강좌' in page.locator('.mini-player .mini-badge').first.inner_text(),
          page.locator('.mini-player .mini-badge').first.inner_text())
    page.click('[data-act="mini-close"]')
    o = overflow(page)
    check(f'{name}: 주간 연습 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'week-{name}.png'), full_page=not mobile)

    # 오늘의 연습 + 박자 메트로놈
    page.click('[data-nav="practice"]')
    page.click('[data-act="ts:6/8"]')
    check(f'{name}: 6/8 선택', '8분음표 6번' in page.content())
    check(f'{name}: 비트 점 6개', page.locator('#beat-dots i').count() == 6)
    page.click('[data-act="metro-toggle"]')
    page.wait_for_timeout(400)
    page.click('[data-act="metro-toggle"]')
    page.click('[data-act="ts:3/4"]')
    check(f'{name}: 3/4 비트 점 3개', page.locator('#beat-dots i').count() == 3)
    check(f'{name}: 14버튼 배치표', page.locator('.aero-pad .pad-btn').count() == 14,
          str(page.locator('.aero-pad .pad-btn').count()))
    check(f'{name}: 14버튼 배치표 안내', '에어로밴드 14버튼 배치' in page.content() and '고급 설정' in page.content())
    o = overflow(page)
    check(f'{name}: 연습 화면 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'practice-{name}.png'), full_page=not mobile)

    # 2026-11-26 오늘의 연습 개편 — 한눈에 보는 3가지 · Day 연동 · 실제 코드 운지표
    page.click('[data-nav="practice"]')
    page.wait_for_selector('.today-step')
    check(f'{name}: 오늘 할 일 3가지 카드', page.locator('.today-step').count() == 3, str(page.locator('.today-step').count()))
    check(f'{name}: Day 칩 7개', page.locator('.day-chip').count() == 7, str(page.locator('.day-chip').count()))
    check(f'{name}: 루틴 5단계 연결 버튼', page.locator('.routine-steps .task-act').count() == 5,
          str(page.locator('.routine-steps .task-act').count()))
    check(f'{name}: 실제 코드 운지표 SVG', page.locator('#today-chords svg.fret-diagram').count() >= 2,
          str(page.locator('#today-chords svg.fret-diagram').count()))
    # 주간 연습에서 1일차를 체크했으므로 오늘은 2일차
    check(f'{name}: 체크한 다음 Day가 오늘 연습', page.locator('.day-chip.on').inner_text().startswith('D2'),
          page.locator('.day-chip.on').inner_text())
    check(f'{name}: 오늘 코드(D2) C·G·Am',
          [x.strip() for x in page.locator('#today-chords .chord-mini b').all_inner_texts()] == ['C', 'G', 'Am'],
          str(page.locator('#today-chords .chord-mini b').all_inner_texts()))
    check(f'{name}: 목표곡 카드에 곡·키·Capo·BPM',
          all(k in page.locator('.today-step').first.inner_text() for k in ('민들레', '남자키', 'Capo +', 'BPM')),
          page.locator('.today-step').first.inner_text()[:120])
    check(f'{name}: ② 오른손 주법 카드', '8비트' in page.locator('.today-step').nth(1).inner_text(),
          page.locator('.today-step').nth(1).inner_text()[:80])
    # Day 3 = C·G·F, F는 바레 대신 약식(xx3211)을 먼저 보여준다
    page.locator('.day-chip').nth(2).click()
    page.wait_for_timeout(150)
    check(f'{name}: Day 3 코드 C·G·F', [x.strip() for x in page.locator('#today-chords .chord-mini b').all_inner_texts()] == ['C', 'G', 'F약식'],
          str(page.locator('#today-chords .chord-mini b').all_inner_texts()))
    check(f'{name}: F 약식 운지 xx3211', 'xx3211' in page.locator('#today-chords').inner_text(),
          page.locator('#today-chords').inner_text()[:160])
    check(f'{name}: 바레 대신 SimplifyChord 안내', 'SimplifyChord' in page.locator('.step-barre').inner_text())
    # ② 주법 영상 보기 → 하단 미니 플레이어
    page.locator('.today-step').nth(1).locator('[data-act^="lesson-play:"]').click()
    page.wait_for_selector('.mini-player iframe')
    v_src = page.locator('.mini-player iframe').first.get_attribute('src') or ''
    check(f'{name}: ② 주법 영상 재생', 'youtube-nocookie.com/embed/' in v_src, v_src)
    page.click('[data-act="mini-close"]')
    # ① 악보 열기 → 악보 모달
    page.locator('.today-step').first.locator('[data-act^="chart:"]').click()
    page.wait_for_selector('.chart-modal')
    check(f'{name}: ① 악보 열기 모달', '원터치' in page.locator('.chart-modal').inner_text())
    page.click('[data-act="close"]')
    # 5단계 루틴 버튼: 메트로놈 켜기(목표곡 템포)
    page.locator('.routine-steps .task-act').nth(0).click()
    page.wait_for_timeout(400)
    check(f'{name}: 루틴 ① 메트로놈 켜기', '정지' in page.locator('[data-act="metro-toggle"]').inner_text(),
          page.locator('[data-act="metro-toggle"]').inner_text())
    check(f'{name}: 목표곡 BPM으로 메트로놈', page.locator('#bpm-label').inner_text().startswith('120'),
          page.locator('#bpm-label').inner_text())
    page.locator('[data-act="metro-toggle"]').click()
    # 루틴 ⑤ 기록 입력 → 기록 폼으로 이동
    page.locator('.routine-steps .task-act').nth(4).click()
    page.wait_for_timeout(600)
    check(f'{name}: 루틴 ⑤ 기록 입력으로 이동', page.evaluate(
        "()=>{const r=document.getElementById('practice-log').getBoundingClientRect();return r.top>-40&&r.top<innerHeight;}"))
    page.evaluate("() => window.scrollTo(0, 0)")
    # 주간 연습 DAY 카드의 '오늘의 연습으로 바로 가기'
    page.click('[data-nav="week"]')
    check(f'{name}: DAY 카드 바로가기 7개', page.locator('.week-day [data-act^="week-day:"]').count() == 7,
          str(page.locator('.week-day [data-act^="week-day:"]').count()))
    page.locator('.week-day').first.locator('[data-act^="week-day:"]').click()
    page.wait_for_timeout(200)
    check(f'{name}: DAY 1 바로가기 → 오늘 연습 D1', page.locator('.day-chip.on').inner_text().startswith('D1'),
          page.locator('.day-chip.on').inner_text())
    check(f'{name}: DAY 1 코드 C·G', [x.strip() for x in page.locator('#today-chords .chord-mini b').all_inner_texts()] == ['C', 'G'],
          str(page.locator('#today-chords .chord-mini b').all_inner_texts()))
    # 홈 히어로 '오늘의 연습 시작' — 장식(.hero:after)이 버튼을 덮어 클릭이 막히던 문제
    page.click('[data-nav="home"]')
    page.wait_for_selector('[data-act="start-practice"]')
    box = page.evaluate("""()=>{const b=document.querySelector('[data-act="start-practice"]');b.scrollIntoView({block:'center'});
        const r=b.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2};}""")
    page.wait_for_timeout(150)
    top = page.evaluate("([x,y])=>{const e=document.elementFromPoint(x,y);return e?e.tagName:'none';}", [box['x'], box['y']])
    check(f'{name}: 히어로 버튼 위를 덮는 요소 없음', top == 'BUTTON', top)
    if mobile:
        page.touchscreen.tap(box['x'], box['y'])
    else:
        page.mouse.click(box['x'], box['y'])
    page.wait_for_timeout(300)
    check(f'{name}: 히어로 버튼 탭 → 오늘의 연습', page.locator('.nav button.active').inner_text() == '오늘의 연습',
          page.locator('.nav button.active').inner_text())

    # 곡 템포로 연습
    page.click('[data-nav="songs"]')
    page.locator('.song-row', has_text='Thank You').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    page.click('button:has-text("이 곡 템포로 연습")')
    page.wait_for_timeout(200)
    body = page.content()
    check(f'{name}: 곡 BPM 넘김', '79 BPM' in body or '79' in body, 'bpm')
    check(f'{name}: 오늘 할 일 3가지 표시', '오늘 할 일 3가지' in body and 'Thank You' in body)

    # 연습 기록 저장
    page.fill('input[name="minutes"]', '12')
    page.fill('textarea[name="memo"]', 'e2e 기록')
    page.click('button:has-text("오늘 연습 저장하기")')
    page.wait_for_timeout(300)
    page.click('[data-nav="logs"]')
    check(f'{name}: 기록 저장', 'e2e 기록' in page.content())

    # 2026-11-22 영상 링크 보강: 영상 버튼이 유튜브 앱이 아니라 하단 미니 플레이어에서 바로 재생
    page.click('[data-nav="songs"]')
    page.select_option('#song-filter', 'all')
    page.fill('#song-search', 'Stand by Me')
    page.wait_for_timeout(200)
    page.locator('.song-row', has_text='Stand by Me').first.locator('button', has_text='영상').click()
    page.wait_for_selector('.mini-player iframe')
    v_src = page.locator('.mini-player iframe').first.get_attribute('src') or ''
    check(f'{name}: 미니 플레이어 영상 재생(Stand by Me)', 'youtube-nocookie.com/embed/z5i9vT8wGY8' in v_src, v_src)
    page.fill('#song-search', '히로인')
    page.wait_for_timeout(200)
    page.locator('.song-row', has_text='히로인').first.locator('button', has_text='영상').click()
    page.wait_for_selector('.mini-player iframe')
    v_src = page.locator('.mini-player iframe').first.get_attribute('src') or ''
    check(f'{name}: 미니 플레이어 영상 재생(히로인)', 'youtube-nocookie.com/embed/107UoVP2fAA' in v_src, v_src)
    page.click('[data-act="mini-close"]')
    page.fill('#song-search', '')
    page.wait_for_timeout(200)

    # 원본 211 + 설정
    page.click('[data-nav="sources"]')
    check(f'{name}: 원본 슬롯 표', page.locator('.source-table tbody tr').count() >= 50)
    o = overflow(page)
    check(f'{name}: 원본 표 가로 넘침 없음(내부 스크롤)', o['sw'] <= o['cw'] + 1, str(o))
    page.click('[data-nav="settings"]')
    check(f'{name}: 백업 화면', '전체 JSON 백업' in page.content() and '악보 설정 CSV' in page.content())

    browser.close()


def run_merge(pw):
    """seedVersion 12 사용자 데이터 → 13 병합: 기록·숙련도 보존 + 악보·영상 링크 추가."""
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.on('pageerror', lambda e: errors.append(f'[merge] pageerror: {e}'))
    page.goto(f'http://127.0.0.1:{PORT}/index.html', wait_until='domcontentloaded')
    legacy = {
        'version': 2, 'seedVersion': 3, 'removedSeedIds': [],
        'songs': [{'id': 'verified-001', 'title': '오늘', 'artist': '오왠 (O.WHEN)', 'sourceIndices': [21],
                   'verification': 'site-top3', 'videoUrl': '', 'audioUrl': '', 'key': '미확정', 'maleKey': '미확정',
                   'bpm': None, 'chords': '', 'chordStatus': '미확인', 'strumming': '', 'level': '버스킹 가능',
                   'tags': [], 'notes': '내 메모', 'setlist': True}],
        'sources': [{'index': i, 'status': '제외' if i == 163 else '미확인', 'url': '', 'note': '', 'songs': []} for i in range(1, 212)],
        'logs': [{'id': 'log-old', 'date': '2026-11-18', 'minutes': 25, 'songId': 'verified-001', 'mode': 'easy',
                  'chords': 'E A', 'strum': '8비트', 'memo': '기존 기록 보존 확인'}],
        'settings': {'mode': 'easy', 'minutes': 25, 'bpm': 60, 'weeklyGoal': 5},
        'completedStages': [], 'selectedRoutine': []
    }
    page.evaluate("s => localStorage.setItem('strum-busking-v2', JSON.stringify(s))", legacy)
    page.reload(wait_until='networkidle')
    page.click('[data-nav="logs"]')
    check('merge: 기존 기록 보존', '기존 기록 보존 확인' in page.content())
    page.click('[data-nav="songs"]')
    page.locator('.song-row', has_text='오늘').first.wait_for()
    check('merge: 남자키 배지 병합', page.locator('.song-row', has_text='오늘').first.inner_text().find('남자키') >= 0)
    state = json.loads(page.evaluate("() => localStorage.getItem('strum-busking-v2')"))
    song = [s for s in state['songs'] if s['id'] == 'verified-001'][0]
    check('merge: seedVersion 29', state['seedVersion'] == 29, str(state['seedVersion']))
    check('merge: 마디 타임라인 병합', bool(song.get('chart', {}).get('timing', {}).get('barTimes')),
          str(song.get('chart', {}).get('timing', {}).get('mode')))
    ty = [s for s in state['songs'] if s['id'] == 'verified-003'][0]
    check('merge: Thank You 가사 35줄·56마디 병합', len((ty.get('lyrics') or {}).get('lines') or []) == 35
          and len(ty.get('chart', {}).get('timing', {}).get('barTimes') or []) == 56,
          f"{len((ty.get('lyrics') or {}).get('lines') or [])}줄 / {len(ty.get('chart', {}).get('timing', {}).get('barTimes') or [])}마디")
    check('merge: Thank You 녹화 반주 병합', ty.get('mrAudioUrl') == 'media/thank-you-mr.mp3', str(ty.get('mrAudioUrl')))
    check('merge: MR 링크 병합', song.get('mrUrl', '').endswith('hwZqHCMmjUM'), str(song.get('mrUrl')))
    check('merge: 숙련도 보존', song['level'] == '버스킹 가능', song['level'])
    check('merge: 사용자 메모 보존', song['notes'] == '내 메모', song['notes'])
    check('merge: 세트리스트 보존', song['setlist'] is True)
    check('merge: 악보 추가(남성 원곡 원키 E)', song.get('chart', {}).get('maleKey') == 'E' and song.get('chart', {}).get('maleShift') == 0, str(song.get('chart', {}).get('maleKey')))
    check('merge: #163 제외 유지', state['sources'][162]['status'] == '제외')
    pik = [s for s in state['songs'] if s['id'] == 'playlist-157'][0]
    check('merge: MR 음원 파일 병합(픽픽)', pik.get('mrAudioUrl') == 'media/pikpik-mr.mp3', str(pik.get('mrAudioUrl')))
    check('merge: 악보 설명 갱신(순수 MR)', '순수 MR' in ([x for x in state['songs'] if x['id'] == 'verified-017'][0].get('chartNote') or ''),
          ([x for x in state['songs'] if x['id'] == 'verified-017'][0].get('chartNote') or '')[:40])
    for sid, fname in (('playlist-173', 'media/jehoda-mr.mp3'), ('playlist-072', 'media/coffee-mr.mp3'),
                       ('verified-017', 'media/toy-mr.mp3'), ('verified-021', 'media/weather-mr.mp3'),
                       ('verified-014', 'media/shannon-sabyeol-mr.mp3'), ('verified-019', 'media/choiyuri-saenggak-mr.mp3'),
                       ('playlist-170', 'media/choiyuri-saenggak-mr.mp3'), ('playlist-174', 'media/choiyuri-saenggak-mr.mp3'),
                       ('restored-100', 'media/goodbye-bye-mr.mp3'), ('playlist-159', 'media/kisum-seo-eoreun-mr.mp3'),
                       ('verified-003', 'media/thank-you-mr.mp3')):
        item = [s for s in state['songs'] if s['id'] == sid][0]
        check(f'merge: MR 음원 병합({sid})', item.get('mrAudioUrl') == fname, str(item.get('mrAudioUrl')))
        check(f'merge: MR 음원 출처({sid})',
              item.get('mrSource') == 'user-recording' and ('AI 보컬 제거' in (item.get('mrNote') or '') or '남자키(-5키)' in (item.get('mrTitle') or '') or 'MDX-NET' in (item.get('mrNote') or '') or '2026-11-27' in (item.get('mrNote') or '')),
              str(item.get('mrNote'))[:60])
        if sid in ('verified-014', 'verified-019', 'playlist-170', 'playlist-174', 'restored-100', 'playlist-159', 'verified-003'):
            check(f'merge: 원키 YouTube MR 비움({sid})', not item.get('mrUrl'), str(item.get('mrUrl')))
    browser.close()


def main():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            run(pw, 'pc', {'width': 1440, 'height': 900})
            run(pw, 'galaxy', {'width': 412, 'height': 915}, mobile=True)
            run_merge(pw)
    finally:
        httpd.shutdown()
    print(f'PASS {len(results)} checks')
    if errors:
        print('CONSOLE ERRORS:')
        for e in errors:
            print(' -', e)
        raise SystemExit(1)
    print('PASS: console error 0')


if __name__ == '__main__':
    main()
