#!/usr/bin/env python3
"""STRUM 아이콘 렌더 — icon.svg 를 512/192/180 PNG 로 굽는다.

실행: python3 tools/make_icons.py
산출: icon-512.png, icon-192.png, icon-180.png, docs/screenshots/icon-preview.png
"""
import pathlib

from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
SVG = (BASE / 'icon.svg').read_text(encoding='utf-8')
SHOTS = BASE / 'docs' / 'screenshots'
SHOTS.mkdir(parents=True, exist_ok=True)


def render(pw, size, out):
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={'width': size, 'height': size}, device_scale_factor=1)
    page = ctx.new_page()
    page.set_content(
        '<!doctype html><html><head><meta charset="utf-8">'
        '<style>html,body{margin:0;padding:0;background:#f8f5ee}'
        f'svg{{display:block;width:{size}px;height:{size}px}}</style></head><body>{SVG}</body></html>',
        wait_until='load',
    )
    page.screenshot(path=str(out), clip={'x': 0, 'y': 0, 'width': size, 'height': size})
    browser.close()


def preview(pw):
    """여러 크기를 한 장에 모아 눈으로 확인하기 위한 미리보기."""
    cells = [(512, '512'), (192, '192'), (180, '180'), (96, '96'), (48, '48'), (32, '32')]
    html = ['<!doctype html><html><head><meta charset="utf-8"><style>',
            'body{margin:0;background:#e8e4d9;font-family:sans-serif;display:flex;gap:22px;'
            'align-items:flex-end;padding:26px;width:1180px}',
            'div{text-align:center;color:#333}span{display:block;font-size:12px;margin-top:6px}',
            '</style></head><body>']
    for size, label in cells:
        html.append(f'<div><div style="width:{size}px;height:{size}px;overflow:hidden;border-radius:{max(6, size//5)}px">{SVG.replace("<svg ", f"<svg width=\"{size}\" height=\"{size}\" ", 1)}</div><span>{label}px</span></div>')
    # maskable 원형 크롭 시뮬레이션
    html.append(
        '<div><div style="width:192px;height:192px;border-radius:50%;overflow:hidden">'
        + SVG.replace('<svg ', '<svg width="192" height="192" ', 1) +
        '</div><span>maskable(원형 크롭)</span></div>')
    html.append('</body></html>')
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={'width': 1180, 'height': 620}, device_scale_factor=2)
    page = ctx.new_page()
    page.set_content(''.join(html), wait_until='load')
    page.screenshot(path=str(SHOTS / 'icon-preview.png'), full_page=True)
    browser.close()


def main():
    with sync_playwright() as pw:
        for size, name in [(512, 'icon-512.png'), (192, 'icon-192.png'), (180, 'icon-180.png')]:
            render(pw, size, BASE / name)
            print('saved', name)
        preview(pw)
        print('saved docs/screenshots/icon-preview.png')
    # 보고용 사본 (아이콘 미리보기)
    import shutil
    for name in ('icon-192.png', 'icon-512.png'):
        shutil.copyfile(BASE / name, SHOTS / name)
        print('saved docs/screenshots/' + name)


if __name__ == '__main__':
    main()
