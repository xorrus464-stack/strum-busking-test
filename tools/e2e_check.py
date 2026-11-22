#!/usr/bin/env python3
"""STRUM 브라우저 검증 (PC + 갤럭시 모바일 에뮬레이션).

실행: python3 tools/e2e_check.py
임시 http.server 를 띄워 실제 페이지를 열고, 콘솔 에러·가로 넘침·핵심 화면을 확인한다.
스크린샷: docs/screenshots/*.png
"""
import http.server
import json
import pathlib
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
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(BASE), **kw)

    def log_message(self, *a):
        pass


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

    # SimplifyChord 슬롯
    page.click('button:has-text("SimplifyChord")')
    page.wait_for_selector('.slot-board')
    check(f'{name}: 슬롯 보드 5칸 이상', page.locator('.slot').count() >= 5)
    page.click('button:has-text("스트로크·퍼커시브")')
    check(f'{name}: 퍼커시브 단계', '4단계로 만드는 퍼커시브' in page.content())
    page.click('button:has-text("근거")')
    check(f'{name}: 근거 링크', page.locator('ul.ev a').count() >= 2)
    page.click('[data-act="close"]')

    # 슬롯 있는 곡
    page.locator('.song-row', has_text='희재').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    page.click('button:has-text("SimplifyChord")')
    check(f'{name}: 슬롯 세팅 가이드', '이렇게 세팅하세요' in page.content())
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
    page.fill('#song-search', '나는 버려질 장난감')
    page.wait_for_timeout(250)
    page.locator('.song-row', has_text='나는 버려질 장난감').first.locator('button', has_text='MR 없음').click()
    page.wait_for_selector('#mr-form')
    check(f'{name}: MR 없음 안내', 'MR이 아직 등록되지 않았습니다' in page.content())
    check(f'{name}: MR 검색 링크', 'youtube.com/results?search_query=' in (page.locator('#mr-form').evaluate("e => e.closest('.modal').innerHTML")))
    page.fill('#mr-form input[name="mrUrl"]', 'https://www.youtube.com/watch?v=IkF6QIQ0Q0A')
    page.click('#mr-form button[type="submit"]')
    page.wait_for_selector('.mini-badge')
    page.wait_for_timeout(200)
    st = json.loads(page.evaluate("() => localStorage.getItem('strum-busking-v2')"))
    edited = [x for x in st['songs'] if x['id'] == 'verified-017'][0]
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

    # 로드맵
    page.click('[data-nav="roadmap"]')
    body = page.content()
    for n in (1, 2, 3, 4):
        check(f'{name}: STAGE {n}', f'STAGE {n}' in body)
    chips = page.locator('.song-chip').count()
    check(f'{name}: 단계별 곡 칩', chips >= 15, f'{chips}')
    o = overflow(page)
    check(f'{name}: 로드맵 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'roadmap-{name}.png'), full_page=not mobile)

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
    check(f'{name}: 원터치 버튼 10개', page.locator('.ot-btn').count() == 10)
    o = overflow(page)
    check(f'{name}: 연습 화면 가로 넘침 없음', o['sw'] <= o['cw'] + 1, str(o))
    page.screenshot(path=str(SHOTS / f'practice-{name}.png'), full_page=not mobile)

    # 곡 템포로 연습
    page.click('[data-nav="songs"]')
    page.locator('.song-row', has_text='Thank You').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    page.click('button:has-text("이 곡 템포로 연습")')
    page.wait_for_timeout(200)
    body = page.content()
    check(f'{name}: 곡 BPM 넘김', '79 BPM' in body or '79' in body, 'bpm')
    check(f'{name}: 오늘의 곡 표시', '오늘의 곡' in body)

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
    check('merge: seedVersion 15', state['seedVersion'] == 15, str(state['seedVersion']))
    check('merge: MR 링크 병합', song.get('mrUrl', '').endswith('hwZqHCMmjUM'), str(song.get('mrUrl')))
    check('merge: 숙련도 보존', song['level'] == '버스킹 가능', song['level'])
    check('merge: 사용자 메모 보존', song['notes'] == '내 메모', song['notes'])
    check('merge: 세트리스트 보존', song['setlist'] is True)
    check('merge: 악보 추가(남성 원곡 원키 E)', song.get('chart', {}).get('maleKey') == 'E' and song.get('chart', {}).get('maleShift') == 0, str(song.get('chart', {}).get('maleKey')))
    check('merge: #163 제외 유지', state['sources'][162]['status'] == '제외')
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
