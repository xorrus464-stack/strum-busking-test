#!/usr/bin/env python3
"""MR 실시간 키 조절 — 실제 오디오 피치가 바뀌는지 측정하는 E2E 테스트 (2026-11-25, v22)

기존 tools/mr_key_ui_test.py 는 라벨·토스트 같은 UI만 봤기 때문에
"AudioWorklet 파라미터만 바꾸고 워클릿은 this.ratio=1 그대로 쓰던" 버그를 놓쳤다.
이 테스트는 440Hz 사인 테스트 음원을 재생하면서 앱이 만든 오디오 그래프의 출력을
AnalyserNode 로 직접 떠서 스펙트럼 최고점(피치)이 실제로 반음만큼 이동하는지 잰다.

확인 항목
 A. AudioWorklet 경로: +2반음 → 440 → 493.9Hz, -5반음(0키 기준) → 329.6Hz
 B. AudioWorklet.addModule 이 실패하는 환경(안드로이드 WebView·커스텀탭 등):
    ScriptProcessorNode 자동 폴백으로 같은 피치 이동이 되는가 · 토스트가 안 뜨는가
 C. 워클릿·폴백 둘 다 불가능한 환경: 토스트 안내 1회 · 페이지 오류 0
 D. 공통: 라벨 변화, 재생 지속, 콘솔 오류 0, 가로 넘침 없음

실행: LD_LIBRARY_PATH=... python3 tools/mr_key_audio_test.py
"""
import http.server
import io
import math
import pathlib
import socketserver
import array
import threading
import urllib.parse
import wave

from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
PORT = 8823
TONE_HZ = 440.0
results = []


def tone_wav(hz=TONE_HZ, seconds=30.0, rate=44100):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        n = int(seconds * rate)
        frames = array.array('h', bytes(4 * n))
        step = 2 * math.pi * hz / rate
        for i in range(n):
            v = int(0.35 * 32767 * math.sin(step * i))
            frames[2 * i] = v
            frames[2 * i + 1] = v
        w.writeframes(frames.tobytes())
    return buf.getvalue()


TONE = tone_wav()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(BASE), **kw)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if urllib.parse.urlparse(self.path).path == '/__test/tone.wav':
            self.send_response(200)
            self.send_header('Content-Type', 'audio/wav')
            self.send_header('Content-Length', str(len(TONE)))
            self.end_headers()
            self.wfile.write(TONE)
            return
        super().do_GET()


def check(name, cond, detail=''):
    results.append((name, bool(cond), detail))
    print(f"{'PASS' if cond else 'FAIL'}  {name}{' — ' + str(detail) if detail else ''}")


# 앱이 만든 오디오 그래프의 destination 연결을 가로채 AnalyserNode 를 하나 달고,
# 어떤 종류의 노드가 소리를 내는지(AudioWorkletNode / ScriptProcessorNode) 기록한다.
TAP_JS = r"""
(() => {
  const nativeConnect = AudioNode.prototype.connect;
  window.__tap = null;
  window.__tapMode = null;
  window.__tapRate = 0;
  window.__tapAttachError = null;
  AudioNode.prototype.connect = function (dest, ...rest) {
    const out = nativeConnect.call(this, dest, ...rest);
    try {
      const ctx = this.context;
      if (dest && ctx && dest === ctx.destination
          && !(this instanceof AnalyserNode) && !(this instanceof GainNode)) {
        {
          const an = ctx.createAnalyser();
          an.fftSize = 16384;
          an.smoothingTimeConstant = 0;
          const mute = ctx.createGain();
          mute.gain.value = 0;
          nativeConnect.call(this, an, 0, 0);
          nativeConnect.call(an, mute, 0, 0);
          nativeConnect.call(mute, ctx.destination, 0, 0);
          window.__tap = an;
          window.__tapRate = ctx.sampleRate;
        }
        window.__tapMode = this.constructor ? this.constructor.name : String(this);
      }
    } catch (e) { window.__tapAttachError = String(e); }
    return out;
  };
  window.__peakHz = () => {
    const an = window.__tap;
    if (!an) return { ok: false, reason: 'no tap' };
    const bins = new Float32Array(an.frequencyBinCount);
    an.getFloatFrequencyData(bins);
    let best = -1, bestVal = -1e9;
    for (let i = 2; i < bins.length; i++) if (bins[i] > bestVal) { bestVal = bins[i]; best = i; }
    const time = new Float32Array(2048);
    an.getFloatTimeDomainData(time);
    let rms = 0;
    for (let i = 0; i < time.length; i++) rms += time[i] * time[i];
    rms = Math.sqrt(rms / time.length);
    return { ok: true, hz: best * window.__tapRate / an.fftSize, db: bestVal, rms, mode: window.__tapMode };
  };
})();
"""


def set_shift(page, target, tries=20):
    """라벨이 target(예 '+2키')이 될 때까지 −/+ 를 누른다. 도달하면 True."""
    for _ in range(tries):
        label = page.locator('#mini-key-label').inner_text().strip()
        if label == target:
            return True
        if not label or not label.endswith('키'):
            page.wait_for_timeout(150)
            continue
        cur = 0 if label == '0키' else int(label.replace('키', '').replace('+', ''))
        want = 0 if target == '0키' else int(target.replace('키', '').replace('+', ''))
        act = 'mini-shift:1' if want > cur else 'mini-shift:-1'
        page.locator(f'[data-act="{act}"]').click()
        page.wait_for_timeout(200)
    return page.locator('#mini-key-label').inner_text().strip() == target


def median_peak(page, tries=7, gap=180):
    vals = []
    for _ in range(tries):
        page.wait_for_timeout(gap)
        m = page.evaluate("() => window.__peakHz()")
        if m and m.get('ok') and m.get('rms', 0) > 0.01:
            vals.append(m)
    if not vals:
        return None
    vals.sort(key=lambda v: v['hz'])
    return vals[len(vals) // 2]


def open_mr(page, label='픽픽'):
    page.click('[data-nav="songs"]')
    page.wait_for_selector('#song-search')
    page.fill('#song-search', label)
    page.wait_for_timeout(500)
    page.locator('.song-row', has_text=label).first.locator('button.mr-on').click()
    page.wait_for_selector('#mini-player')


def use_tone(page):
    """미니 플레이어의 audio 요소를 440Hz 테스트 음원으로 바꾼다(그래프는 그대로)."""
    page.wait_for_selector('#mini-audio', state='attached')
    page.evaluate("""() => new Promise((resolve) => {
      const a = document.getElementById('mini-audio');
      a.loop = false;
      a.src = '/__test/tone.wav';
      a.load();
      const go = () => a.play().then(resolve).catch(resolve);
      if (a.readyState >= 2) go(); else a.addEventListener('canplay', go, { once: true });
    })""")
    page.wait_for_function("() => {const a=document.getElementById('mini-audio');return a && a.currentTime > 0.2;}", timeout=15000)


def toasts(page):
    return page.evaluate("""() => [...document.querySelectorAll('.notice,.toast,.mini-toast,[role=status]')]
        .map(x => (x.textContent || '').trim()).filter(Boolean)""")


def close_toasts(page):
    page.evaluate("""() => document.querySelectorAll('.notice,.toast').forEach(n => n.remove())""")


def near(hz, expect, tol=0.035):
    return hz is not None and abs(hz - expect) / expect <= tol


def run_case(browser, name, view, mobile, init_js=None, expect_mode=None, expect_toast=False):
    pitch = not expect_toast
    ctx = browser.new_context(viewport=view,
                              user_agent=('Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 '
                                          '(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36') if mobile else None,
                              is_mobile=mobile, has_touch=mobile, service_workers='block')
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    page.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
    page.add_init_script(TAP_JS)
    if init_js:
        page.add_init_script(init_js)
    page.goto(f'http://127.0.0.1:{PORT}/index.html', wait_until='networkidle')
    page.evaluate("() => localStorage.clear()")
    page.reload(wait_until='networkidle')
    open_mr(page)
    page.wait_for_selector('#mini-key')
    use_tone(page)

    base = None
    if pitch:
        # 그래프는 처음 키를 누를 때 만들어진다 → +1/−1 로 깨운 뒤 0키 기준을 잰다
        page.locator('[data-act="mini-shift:1"]').click()
        page.wait_for_timeout(250)
        page.locator('[data-act="mini-shift:-1"]').click()
        page.wait_for_timeout(400)
        base = median_peak(page)
        check(f'{name}: 기준 440Hz 재생 확인', base and near(base['hz'], TONE_HZ, 0.02),
              base and f"{base['hz']:.1f}Hz rms={base['rms']:.3f} mode={base['mode']}")
    close_toasts(page)

    if not pitch:
        # 키 조절이 아예 불가능한 환경: 안내만 하고 오류 없이 원음 재생이어야 한다
        page.locator('[data-act="mini-shift:1"]').click()
        page.locator('[data-act="mini-shift:1"]').click()
        page.wait_for_timeout(500)
        hold = median_peak(page)
        check(f'{name}: 원음(440Hz) 그대로 재생', hold and near(hold['hz'], TONE_HZ, 0.02), hold and f"{hold['hz']:.1f}Hz")
        check(f'{name}: 키 조절 불가 안내 토스트', any('이 브라우저에서는 키 조절' in t for t in toasts(page)), toasts(page))
        check(f'{name}: 라벨 0키로 되돌림', page.locator('#mini-key-label').inner_text().strip() == '0키',
              page.locator('#mini-key-label').inner_text())
        check(f'{name}: 페이지 오류 0', len(errors) == 0, '; '.join(errors[:3]))
        ctx.close()
        return

    # +2반음
    check(f'{name}: +2키로 맞춤', set_shift(page, '+2키'), page.locator('#mini-key-label').inner_text())
    page.wait_for_timeout(400)
    up = median_peak(page)
    want_up = TONE_HZ * 2 ** (2 / 12)
    check(f'{name}: +2반음 → {want_up:.1f}Hz', up and near(up['hz'], want_up),
          up and f"{up['hz']:.1f}Hz label={page.locator('#mini-key-label').inner_text().strip()} mode={up['mode']}")
    check(f'{name}: +2반음 라벨', page.locator('#mini-key-label').inner_text().strip() == '+2키')
    check(f'{name}: +2반음에 안내(불가) 토스트 없음', not any('이 브라우저에서는' in t for t in toasts(page)), toasts(page))
    if expect_mode:
        check(f'{name}: 그래프 종류 {expect_mode}', up and up['mode'] == expect_mode, up and up['mode'])

    # 다시 0키 → 440Hz 복귀
    set_shift(page, '0키')
    page.wait_for_timeout(500)
    back = median_peak(page)
    check(f'{name}: 0키 복귀 → 440Hz', back and near(back['hz'], TONE_HZ, 0.02), back and f"{back['hz']:.1f}Hz")

    # -5반음
    check(f'{name}: -5키로 맞춤', set_shift(page, '-5키'), page.locator('#mini-key-label').inner_text())
    page.wait_for_timeout(400)
    down = median_peak(page)
    want_down = TONE_HZ * 2 ** (-5 / 12)
    check(f'{name}: -5반음 → {want_down:.1f}Hz', down and near(down['hz'], want_down),
          down and f"{down['hz']:.1f}Hz label={page.locator('#mini-key-label').inner_text().strip()}")

    # 재생 지속
    t0 = page.evaluate("() => document.getElementById('mini-audio').currentTime")
    page.wait_for_timeout(700)
    t1 = page.evaluate("() => document.getElementById('mini-audio').currentTime")
    check(f'{name}: 키를 바꿔도 재생 계속', t1 > t0 + 0.2, f'{t0:.2f} → {t1:.2f}')

    check(f'{name}: 페이지 오류 0', len(errors) == 0, '; '.join(errors[:3]))

    # 연타(중복 ensurePitch) 방어: 12번 빠르게 눌러도 예외 없음
    for i in range(12):
        page.locator(f'[data-act="mini-shift:{1 if i % 2 == 0 else -1}"]').click()
    page.wait_for_timeout(300)
    check(f'{name}: -/+ 연타에도 오류 없음', len(errors) == 0, '; '.join(errors[:3]))

    if mobile:
        w = page.evaluate("() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")
        check(f'{name}: 가로 넘침 없음', w['sw'] <= w['cw'] + 1, w)
    ctx.close()


def run_reopen_case(browser, name, view, mobile, init_js=None, expect_mode=None):
    """미니 플레이어를 닫었다가 다시 열어도(새 <audio> 요소) 키 조절이 계속 동작해야 한다."""
    ctx = browser.new_context(viewport=view,
                              user_agent=('Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 '
                                          '(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36') if mobile else None,
                              is_mobile=mobile, has_touch=mobile, service_workers='block')
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    page.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
    page.add_init_script(TAP_JS)
    if init_js:
        page.add_init_script(init_js)
    page.goto(f'http://127.0.0.1:{PORT}/index.html', wait_until='networkidle')
    page.evaluate("() => localStorage.clear()")
    page.reload(wait_until='networkidle')

    for round_ in (1, 2):
        open_mr(page)
        page.wait_for_selector('#mini-key')
        use_tone(page)
        check(f'{name} {round_}번째 재생: 0키 기준', set_shift(page, '0키'), page.locator('#mini-key-label').inner_text())
        check(f'{name} {round_}번째 재생: +2키로 맞춤', set_shift(page, '+2키'), page.locator('#mini-key-label').inner_text())
        page.wait_for_timeout(400)
        up = median_peak(page)
        check(f'{name} {round_}번째 재생: +2반음 → 493.9Hz', up and near(up['hz'], TONE_HZ * 2 ** (2 / 12)),
              up and f"{up['hz']:.1f}Hz mode={up['mode']}")
        check(f'{name} {round_}번째 재생: 불가 토스트 없음', not any('이 브라우저에서는' in t for t in toasts(page)), toasts(page))
        if expect_mode:
            check(f'{name} {round_}번째 재생: 그래프 {expect_mode}', up and up['mode'] == expect_mode, up and up['mode'])
        page.click('[data-act="mini-close"]')
        page.wait_for_timeout(400)
    check(f'{name}: 페이지 오류 0', len(errors) == 0, '; '.join(errors[:3]))
    ctx.close()


def main():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
            pc = {'width': 1280, 'height': 900}
            gal = {'width': 412, 'height': 915}

            run_case(browser, 'PC/worklet', pc, False, expect_mode='AudioWorkletNode')
            run_case(browser, 'Galaxy/worklet', gal, True, expect_mode='AudioWorkletNode')

            # 안드로이드 WebView·커스텀탭 재현: addModule 이 거부되는 환경
            AW_FAIL = "(() => { if (window.AudioWorklet) AudioWorklet.prototype.addModule = function () { return Promise.reject(new DOMException('simulated addModule failure', 'NotSupportedError')); }; })();"
            run_case(browser, 'PC/폴백(addModule 실패)', pc, False, init_js=AW_FAIL, expect_mode='ScriptProcessorNode')
            run_case(browser, 'Galaxy/폴백(addModule 실패)', gal, True, init_js=AW_FAIL, expect_mode='ScriptProcessorNode')

            # 둘 다 불가: 안내만 하고 죽지 않아야 한다
            BOTH_FAIL = AW_FAIL.replace('})();', """
  if (window.AudioContext) AudioContext.prototype.createScriptProcessor = function () { throw new Error('simulated script processor failure'); };
  if (window.webkitAudioContext) webkitAudioContext.prototype.createScriptProcessor = function () { throw new Error('simulated script processor failure'); };
})();""")
            run_case(browser, 'Galaxy/둘 다 불가', gal, True, init_js=BOTH_FAIL, expect_toast=True)

            # 닫았다 다시 열기(새 audio 요소 + 재사용 컨텍스트)
            run_reopen_case(browser, 'Galaxy/worklet 재열기', gal, True, expect_mode='AudioWorkletNode')
            run_reopen_case(browser, 'Galaxy/폴백 재열기', gal, True, init_js=AW_FAIL, expect_mode='ScriptProcessorNode')
            browser.close()
    finally:
        httpd.shutdown()
    bad = [r for r in results if not r[1]]
    print(f'RESULT {"PASS" if not bad else "FAIL"} ({len(results) - len(bad)}/{len(results)})')
    raise SystemExit(0 if not bad else 1)


if __name__ == '__main__':
    main()
