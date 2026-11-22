#!/usr/bin/env python3
"""MR 영상이 실제로 임베드 재생되는지 확인한다 (YouTube IFrame API).

oEmbed 200 은 '존재'만 알려 주고, TJ노래방처럼 임베드를 막은 영상도 200을 돌려준다.
그래서 실제 앱과 같은 방식(iframe + IFrame API)으로 재생 가능 여부를 확인한다.
결과: tmp/embed_status.json  {"<videoId>": "PLAYS"|"ERROR150"|...}

실행: python3 tools/mr_embed_check.py [--batch 16]
"""
import argparse
import http.server
import json
import pathlib
import socketserver
import threading

from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
OUT = BASE / 'tmp' / 'embed_status.json'
PORT = 8791


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(BASE), **kw)

    def log_message(self, *a):
        pass


def ids_from_file(path):
    data = json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    if isinstance(data, dict):
        data = list(data.keys())
    return data


def ids_to_check():
    songs = json.loads((BASE / 'data' / 'songs.seed.json').read_text(encoding='utf-8'))
    seen = []
    for s in songs:
        url = s.get('mrUrl') or ''
        if 'watch?v=' in url:
            vid = url.split('watch?v=')[1][:11]
            if vid not in seen:
                seen.append(vid)
    return seen


def check(browser, ids, wait_ms=9000):
    page = browser.new_page(viewport={'width': 1000, 'height': 900})
    page.goto(f'http://127.0.0.1:{PORT}/mrcheck.html?ids=' + ','.join(ids),
              wait_until='domcontentloaded')
    page.wait_for_timeout(wait_ms)
    text = page.locator('#out').text_content() or ''

    page.close()
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            vid, status = parts
            if status in ('READY', 'PLAYS'):
                out[vid] = 'PLAYS'
            else:
                out[vid] = status
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', type=int, default=16)
    ap.add_argument('--wait', type=int, default=12000)
    ap.add_argument('--ids-file', default='')
    args = ap.parse_args()
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    ids = ids_from_file(args.ids_file) if args.ids_file else ids_to_check()
    known = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    todo = [i for i in ids if i not in known]
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for n in range(0, len(todo), args.batch):
                chunk = todo[n:n + args.batch]
                res = check(browser, chunk, args.wait)
                known.update(res)
                OUT.write_text(json.dumps(known, ensure_ascii=False, indent=1), encoding='utf-8')
                plays = sum(1 for k, v in known.items() if v == 'PLAYS')
                print(f'[{n + len(chunk)}/{len(todo)}] plays {plays}/{len(known)}', flush=True)
            browser.close()
    finally:
        httpd.shutdown()
    print('PLAYS', sum(1 for v in known.values() if v == 'PLAYS'), '/', len(known))


if __name__ == '__main__':
    main()
