#!/usr/bin/env python3
"""악보 마디 타임스탬프(timing) 계산 — MR 재생과 마디·코드 색깔을 맞추기 위한 데이터 (2026-11-27).

곡마다 `chart.timing` 을 만든다.
  mode 'section'   : 악보 섹션 이름에 적힌 실측 구간(`(0:22–0:42)`)에서 마디 시각을 계산. 가장 정확.
  mode 'bpm-local' : 저장소 media/ 음원 파일이 있는 곡. 실제 길이(mutagen) + BPM + 첫 박(onset) 오프셋.
  mode 'bpm-yt'    : 유튜브 MR만 있는 곡. BPM·박자 기반 추정(전주·간주 오차 가능, 화면에 안내 배지).
  mode 'none'      : BPM이 없어 계산할 수 없는 곡(타임라인 표시하지 않음).

저장 값
  bpm, beats, barSec, offsetSec, durationSec, bars(악보 마디 수), cycle(곡이 악보보다 길어 반복 표시),
  barTimes[[start,end], ...] (mode section·bpm-local은 실제 시각, bpm-yt는 계산값), note

실행: python3 tools/apply_chart_timing_2026_11_27.py [--write]
"""
import json
import pathlib
import re
import sys

BASE = pathlib.Path(__file__).resolve().parents[1]
SEED_JS = BASE / 'src' / 'seed.js'
SEED_JSON = BASE / 'data' / 'songs.seed.json'
DATE = '2026-11-27'

TIME_RE = re.compile(r'(\d+):(\d{2})\s*[–\-~]\s*(\d+):(\d{2})')
YT_BADGE = ('유튜브 MR은 전주·간주 길이에 따라 오차가 날 수 있어요. 녹화 음원을 주시면 정확히 맞춰드립니다.')


def load_seed():
    txt = SEED_JS.read_text(encoding='utf-8')
    dec = json.JSONDecoder()
    i = txt.index('window.STRUM_SEED')
    raw = txt[txt.index('=', i) + 1:]
    k = len(raw) - len(raw.lstrip())
    seed, end = dec.raw_decode(raw[k:])
    return seed, raw[k + end:]


def save_seed(seed, tail):
    SEED_JS.write_text('window.STRUM_SEED = '
                       + json.dumps(seed, ensure_ascii=False, separators=(',', ':')) + tail,
                       encoding='utf-8')


def beats_of(ts):
    return 6 if ts == '6/8' else 3 if ts == '3/4' else 4


def mmss(a, b):
    return int(a) * 60 + int(b)


def audio_length(path):
    try:
        import mutagen.mp3
        return float(mutagen.mp3.MP3(str(path)).info.length)
    except Exception:
        pass
    try:
        import mutagen
        return float(mutagen.File(str(path)).info.length)
    except Exception:
        return None


def first_beat(path, bar_sec):
    """첫 박 위치를 잡는다(전주가 있는 녹음에서 마디 격자를 맞추기 위해)."""
    try:
        import librosa
        import numpy as np
    except Exception:
        return None, None
    try:
        y, sr = librosa.load(str(path), mono=True, duration=40, sr=22050)
        if not len(y):
            return None, None
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        times = librosa.times_like(onset_env, sr=sr)
        # 첫 5초 안의 가장 센 onset → 곡 시작(첫 다운비트)으로 본다.
        head = onset_env[:int(5 * sr / 512) + 1]
        if not len(head) or float(np.max(head)) <= 0:
            return None, None
        idx = int(np.argmax(head))
        first = float(times[idx]) if idx < len(times) else 0.0
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
        tempo = float(np.atleast_1d(tempo)[0])
        return round(max(0.0, first), 2), round(tempo, 1)
    except Exception:
        return None, None


def build_timing(chart, song):
    ts = chart.get('timeSignature') or '4/4'
    bpm = chart.get('bpm') or song.get('bpm') or 0
    beats = beats_of(ts)
    sections = chart.get('sections') or []
    bars = sum(len(s['bars']) for s in sections)
    audio = song.get('mrAudioUrl') or song.get('fullAudioUrl') or ''
    audio_path = (BASE / audio) if audio else None
    duration = audio_length(audio_path) if audio_path and audio_path.exists() else None
    timing = {'date': DATE, 'timeSignature': ts, 'beats': beats, 'bars': bars,
              'bpm': bpm if bpm else None, 'audio': audio or '', 'durationSec': round(duration, 2) if duration else None}
    if not bpm:
        timing.update({'mode': 'none', 'source': 'bpm 없음',
                       'note': 'BPM이 확인되지 않아 마디 타임라인을 표시하지 않습니다.'})
        return timing
    bar_sec = beats * 60.0 / float(bpm)

    # ── 1) 섹션 이름에 적힌 실측 구간 ──────────────────────────
    have = sum(1 for s in sections if TIME_RE.search(s['name']))
    if sections and have == len(sections):
        bar_times, cursor, ok = [], None, True
        for sec in sections:
            m = TIME_RE.search(sec['name'])
            start = mmss(m.group(1), m.group(2))
            end = mmss(m.group(3), m.group(4))
            n = len(sec['bars'])
            # 구간 표기가 1초쯤 겹치는 곡이 있다(예: 도입 0:01–0:18 / A1 0:17–0:40).
            # 마디 시각이 뒤로 가지 않게 앞 구간 끝에서 이어 붙인다.
            if cursor is not None and start < cursor:
                start = cursor
            if end <= start:
                end = start + n * bar_sec
            if n <= 0:
                ok = False
                break
            step = (end - start) / n
            for i in range(n):
                bar_times.append([round(start + i * step, 2), round(start + (i + 1) * step, 2)])
            cursor = end
        if ok and len(bar_times) == bars:
            span = bar_times[-1][1] - bar_times[0][0]
            timing.update({
                'mode': 'section', 'source': '녹화·구간 표기 실측',
                'barSec': round(span / bars, 3),
                'offsetSec': bar_times[0][0],
                'barTimes': bar_times,
                'cycle': bool(duration and span < duration * 0.9),
                'note': '악보 섹션에 적힌 실제 구간 시각으로 마디를 맞췄습니다.',
            })
            return timing

    # ── 2) 저장소 음원 파일 ────────────────────────────────────
    offset, measured = (None, None)
    if audio_path and audio_path.exists():
        offset, measured = first_beat(audio_path, bar_sec)
    if audio_path and duration:
        off = offset if offset is not None and offset < 12 else 0.0
        n_audio = max(1, int((duration - off) / bar_sec))
        bar_times = [[round(off + i * bar_sec, 2), round(off + (i + 1) * bar_sec, 2)] for i in range(n_audio)]
        span = bar_times[-1][1] - bar_times[0][0]
        timing.update({
            'mode': 'bpm-local', 'source': '음원 길이 + BPM + 첫 박',
            'barSec': round(bar_sec, 3), 'offsetSec': round(off, 2),
            'barTimes': bar_times,
            'audioBars': n_audio,
            'measuredTempo': measured,
            'cycle': n_audio > bars,
            'note': ('음원 첫 박에 마디 격자를 맞췄습니다.' if off else '음원 시작(0초)부터 마디 격자를 맞췄습니다.')
                    + (' 악보 마디가 곡 길이보다 짧아, 곡이 길면 악보 마디가 처음부터 다시 돌아가며 표시됩니다.'
                       if n_audio > bars else ''),
        })
        return timing

    # ── 3) 유튜브 MR 추정 ─────────────────────────────────────
    bar_times = [[round(i * bar_sec, 2), round((i + 1) * bar_sec, 2)] for i in range(bars)]
    timing.update({
        'mode': 'bpm-yt', 'source': 'BPM·박자 추정', 'barSec': round(bar_sec, 3),
        'offsetSec': 0, 'barTimes': bar_times, 'cycle': False, 'badge': YT_BADGE,
        'note': 'MR 영상의 전주 길이를 몰라 0초부터 BPM으로 계산한 추정값입니다.',
    })
    return timing


def main():
    write = '--write' in sys.argv
    seed, tail = load_seed()
    songs = seed['songs']
    charts = [s for s in songs if isinstance(s.get('chart'), dict) and s['chart'].get('sections')]
    modes = {}
    for s in charts:
        t = build_timing(s['chart'], s)
        # JSON 크기를 줄이려고 같은 시각 배열은 그대로 두되, 소수 둘째 자리로 맞춘다.
        s['chart']['timing'] = t
        modes[t['mode']] = modes.get(t['mode'], 0) + 1
    print('timing 모드:', modes)
    for m in ('section', 'bpm-local'):
        for s in charts:
            t = s['chart']['timing']
            if t['mode'] == m:
                print(f"  [{m}] {s['id']:16s} {s['title'][:26]:28s} bpm={t['bpm']} barSec={t['barSec']} "
                      f"offset={t['offsetSec']} bars={t['bars']}/{len(t['barTimes'])} "
                      f"dur={t['durationSec']} cycle={t['cycle']}")
    if write:
        meta = seed['meta']
        counts = {}
        for s in charts:
            t = s['chart']['timing']
            counts[t['mode']] = counts.get(t['mode'], 0) + 1
        meta['chartTiming'] = {
            'date': DATE,
            'chartCount': len(charts),
            'modes': counts,
            'sectionBased': [s['id'] for s in charts if s['chart']['timing']['mode'] == 'section'],
            'localAudio': [s['id'] for s in charts if s['chart']['timing']['mode'] == 'bpm-local'],
            'estimated': [s['id'] for s in charts if s['chart']['timing']['mode'] == 'bpm-yt'],
            'noBpm': [s['id'] for s in charts if s['chart']['timing']['mode'] == 'none'],
            'badge': YT_BADGE,
            'note': '마디 타임스탬프는 섹션 실측 구간 → 저장소 음원 실측(BPM·첫 박) → 유튜브 추정 순으로 채웠습니다.',
        }
        save_seed(seed, tail)
        SEED_JSON.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (BASE / 'data' / 'metadata.json').write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('written')
    else:
        print('(dry run — --write 로 반영)')


if __name__ == '__main__':
    main()
