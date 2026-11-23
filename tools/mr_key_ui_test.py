#!/usr/bin/env python3
"""MR 음원(MP3)·실시간 키 조절 UI 검증 (PC + 갤럭시 모바일 크기).

확인 항목
 1. MP3 MR 곡(픽픽)에서 미니 플레이어에 키 조절 바(−/0키/+)가 뜨는가
 2. +를 누르면 라벨이 +1키로 바뀌고, 계속 누르면 +6키에서 멈추는가
 3. −를 누르면 0키로 돌아오는가
 4. 키를 바꿔도 재생이 계속되는가(audio.currentTime 증가) · 콘솔 오류 0
 5. 유튜브 iframe MR 곡에서는 키 조절 대신 안내 문구가 뜨는가
 6. 폭 412px(갤럭시)에서 가로 넘침이 없는가

실행: python3 tools/mr_key_ui_test.py
"""
import http.server
import json
import pathlib
import socketserver
import threading

from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
PORT = 8794
SHOTS = BASE / 'docs' / 'screenshots'
results = []


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(BASE), **kw)

    def log_message(self, *a):
        pass


def check(name, cond, detail=''):
    results.append((name, bool(cond), detail))
    print(f"{'PASS' if cond else 'FAIL'}  {name}{' — ' + str(detail) if detail else ''}")


def open_song_mr(page, label):
    page.click('[data-nav="songs"]')
    page.wait_for_selector('#song-search')
    page.fill('#song-search', label)
    page.wait_for_timeout(500)
    row = page.locator('.song-row', has_text=label).first
    row.locator('button.mr-on').click()
    page.wait_for_selector('#mini-player')


def main():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
            for name, view, mobile in (('pc', {'width': 1440, 'height': 900}, False),
                                       ('galaxy', {'width': 412, 'height': 915}, True)):
                ctx = browser.new_context(viewport=view,
                                          user_agent=('Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 '
                                                      '(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36') if mobile else None,
                                          is_mobile=mobile, has_touch=mobile, service_workers='block')
                page = ctx.new_page()
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
                # 마이크/오디오 자동재생 허용
                page.goto(f'http://127.0.0.1:{PORT}/index.html', wait_until='networkidle')
                page.evaluate("() => localStorage.clear()")
                page.reload(wait_until='networkidle')

                # 1) MP3 MR — 픽픽(media/pikpik-mr.mp3)
                open_song_mr(page, '픽픽')
                page.wait_for_selector('#mini-key')
                check(f'{name}: MP3 MR에 키 조절 바 표시', page.locator('#mini-key').count() == 1)
                check(f'{name}: 처음 라벨 0키', page.locator('#mini-key-label').inner_text().strip() == '0키')
                page.wait_for_function("() => {const a=document.getElementById('mini-audio');return a && a.readyState>=1;}", timeout=30000)
                page.evaluate("() => {const a=document.getElementById('mini-audio');return a.play().catch(()=>{});}")
                page.wait_for_timeout(700)
                t0 = page.evaluate("() => document.getElementById('mini-audio').currentTime")
                for _ in range(3):
                    page.locator('[data-act="mini-shift:1"]').click()
                    page.wait_for_timeout(250)
                check(f'{name}: +3번 → +3키', page.locator('#mini-key-label').inner_text().strip() == '+3키',
                      page.locator('#mini-key-label').inner_text())
                page.wait_for_timeout(1200)
                t1 = page.evaluate("() => document.getElementById('mini-audio').currentTime")
                check(f'{name}: 키를 바꿔도 재생 계속', t1 > t0, f'{t0:.2f} → {t1:.2f}')
                for _ in range(6):
                    page.locator('[data-act="mini-shift:1"]').click()
                    page.wait_for_timeout(120)
                check(f'{name}: +6키에서 멈춤', page.locator('#mini-key-label').inner_text().strip() == '+6키',
                      page.locator('#mini-key-label').inner_text())
                for _ in range(12):
                    page.locator('[data-act="mini-shift:-1"]').click()
                    page.wait_for_timeout(120)
                check(f'{name}: -6키에서 멈춤', page.locator('#mini-key-label').inner_text().strip() == '-6키',
                      page.locator('#mini-key-label').inner_text())
                wav = page.evaluate("() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")
                check(f'{name}: 가로 넘침 없음', wav['sw'] <= wav['cw'] + 1, wav)
                page.screenshot(path=str(SHOTS / f'mr-key-{name}.png'))
                page.click('[data-act="mini-close"]')

                # 2) 유튜브 iframe MR — 안내 문구
                open_song_mr(page, '오늘')
                page.wait_for_selector('#mini-player')
                check(f'{name}: 유튜브 MR에는 키 조절 바 없음', page.locator('#mini-key').count() == 0)
                check(f'{name}: 유튜브 MR에는 안내 문구', page.locator('.mini-key-note').count() == 1,
                      page.locator('.mini-key-note').inner_text() if page.locator('.mini-key-note').count() else '')
                check(f'{name}: 콘솔 오류 0', len(errors) == 0, '; '.join(errors[:3]))
                ctx.close()
            browser.close()
    finally:
        httpd.shutdown()
    bad = [r for r in results if not r[1]]
    print(f'RESULT {"PASS" if not bad else "FAIL"} ({len(results) - len(bad)}/{len(results)})')
    raise SystemExit(0 if not bad else 1)


if __name__ == '__main__':
    main()
