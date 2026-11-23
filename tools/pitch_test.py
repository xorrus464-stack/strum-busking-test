#!/usr/bin/env python3
"""MR 실시간 키 조절(피치 시프터) 검증.

tools/pitch_test.html 을 로컬 서버로 열어
  - 2반음 올림/5반음 내림에서 실제 주파수가 바뀌는지
  - 템포(출력 길이)가 그대로인지
  - 0키에서는 원음이 그대로 나오는지
  - +6반음 경계에서 값이 깨지지 않는지
  - AudioWorklet 모듈 등록·노드 생성이 되는지
를 확인한다.

실행: python3 tools/pitch_test.py
"""
import functools
import http.server
import pathlib
import socketserver
import threading

from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
PORT = 8792


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(BASE), **kw)

    def log_message(self, *a):
        pass


def main():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
            page = browser.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{PORT}/tools/pitch_test.html', wait_until='domcontentloaded')
            page.wait_for_function("() => document.getElementById('out').textContent.includes('RESULT')",
                                   timeout=60000)
            txt = page.locator('#out').text_content()
            browser.close()
    finally:
        httpd.shutdown()
    print(txt)
    ok = 'RESULT PASS' in (txt or '') and 'FAIL' not in (txt or '')
    print('console errors:', errors)
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
