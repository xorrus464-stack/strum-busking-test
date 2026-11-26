#!/usr/bin/env python3
"""라이브(GitHub Pages) 실측 — 최적 14버튼 · 마디 클릭 이동 · 배속 · 색깔 싱크 · 주법 연결."""
import json
from playwright.sync_api import sync_playwright

URL = 'https://xorrus464-stack.github.io/strum-busking-test/'
errors = []


def run(pw, label, viewport, mobile=False):
    b = pw.chromium.launch()
    ctx = b.new_context(viewport=viewport, is_mobile=mobile, has_touch=mobile,
                        device_scale_factor=2 if mobile else 1)
    page = ctx.new_page()
    page.on('console', lambda m: errors.append(f'[{label}] {m.type}: {m.text}') if m.type == 'error' else None)
    page.on('pageerror', lambda e: errors.append(f'[{label}] pageerror: {e}'))
    page.goto(URL, wait_until='networkidle')
    seed = page.evaluate("() => ({v: window.STRUM_SEED.meta.seedVersion, btns: window.STRUM_SEED.meta.buttonSet})")
    print(f'[{label}] seed', seed['v'], 'buttons', ' '.join(seed['btns']))
    assert seed['v'] == 28 and 'B' in seed['btns'] and 'Bdim' not in seed['btns'], seed

    page.click('[data-nav="songs"]')
    page.fill('#song-search', 'Good Bye-Bye')
    page.wait_for_timeout(400)
    page.locator('.song-row').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    print(f'[{label}] pad', page.locator('.aero-pad .pad-btn').count(),
          'strip', page.locator('#aero-strip .pad-btn').count(),
          'bars', page.locator('#chart-bars .bar').count(),
          'times', page.locator('#chart-bars .bar-time').count())
    page.locator('.chart-modal').locator('button', has_text='MR 듣기').click()
    page.wait_for_selector('.mini-player audio#mini-audio')
    page.wait_for_function("() => { const a=document.querySelector('#mini-audio'); return !!a && a.readyState>=1 && a.duration>200; }", timeout=30000)
    page.click('.mini-rate .rate-btn[data-rate="0.7"]')
    page.wait_for_timeout(400)
    r = page.evaluate("() => document.querySelector('#mini-audio').playbackRate")
    print(f'[{label}] rate 0.7 →', r)
    page.click('.mini-rate .rate-btn[data-rate="1"]')
    page.locator('#chart-bars .bar').nth(9).click()
    page.wait_for_timeout(1200)
    st = page.evaluate("""() => {const a=document.querySelector('#mini-audio'); return {
        t: Math.round(a.currentTime*10)/10, paused: a.paused,
        nowBars: document.querySelectorAll('#chart-bars .bar.now').length,
        nowPad: document.querySelectorAll('.aero-strip .pad-btn.now').length,
        label: (document.getElementById('chart-now-label')||{}).textContent};}""")
    print(f'[{label}] bar10 click →', st)
    page.screenshot(path=f'/workspace/strum-busking-test/docs/screenshots/live-chart-sync-{label}.png')
    page.click('[data-act="mini-close"]')
    page.click('[data-act="close"]')

    page.fill('#song-search', 'Thank You')
    page.wait_for_timeout(350)
    page.locator('.song-row').first.locator('button', has_text='악보').click()
    page.wait_for_selector('.chart-modal')
    lesson = page.locator('.lesson-link').inner_text()
    print(f'[{label}] lesson', lesson.replace('\n', ' / ')[:60])
    page.locator('.lesson-link button').click()
    page.wait_for_selector('.mini-player iframe', timeout=25000)
    src = page.locator('.mini-player iframe').first.get_attribute('src')
    print(f'[{label}] lesson video', src[:70])
    page.screenshot(path=f'/workspace/strum-busking-test/docs/screenshots/live-lesson-{label}.png')
    ctx.close()
    b.close()


with sync_playwright() as pw:
    run(pw, 'pc', {'width': 1440, 'height': 900})
    run(pw, 'galaxy', {'width': 412, 'height': 915}, mobile=True)
print('console errors:', errors)
assert not errors, errors
