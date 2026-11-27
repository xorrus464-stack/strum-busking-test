#!/usr/bin/env python3
"""Thank You(Dido) — 주성 님 2026-11-27 녹화(2:52, Sam Backing Tracks 'Acoustic Karaoke') 반영.

녹화에서 뽑은 반주를 media/thank-you-mr.mp3 로 넣고(-16.8 LUFS), 곡의 악보를
도입~아웃트로 56마디 전곡으로 다시 세운다. 마디 시각은 녹화 실측(80.0BPM · 4/4 · 첫 박 0.04초).

  · 곡: verified-003 / Thank You / Dido
  · 키: B장조(원곡과 같은 조) — 14버튼 G폼 Capo +4로 전곡이 버튼만으로 완주
  · 코드: 실측 bass·chroma + 공개 코드표(chordharbor) 대조
      도입 G#m×2 / 1절 G#m · (F#→B)×3 · G#m / 2절 G#m · G#m · (G#m→E, F#→B)×3
      간주 G#m→E · E / 후렴 B E B E B E D#m C#m / 3절(후렴 진행) · 후렴 2 · 후렴 3 / 아웃트로 B B
  · 가사: 영상 자막 블록(1절 10.5s, 2절 34.0s, 후렴 63.7s, 3절 93.6s, 후렴 117.0s)과
      마디 그리드에 1:1로 붙인 35줄 타임라인(절 1줄=1마디, 후렴 1줄=2마디).

실행: python3 tools/apply_thank_you_recording_2026_11_27.py [--write]
"""
import json
import pathlib
import sys
from collections import Counter

BASE = pathlib.Path(__file__).resolve().parents[1]
SEED_JS = BASE / 'src' / 'seed.js'
SEED_JSON = BASE / 'data' / 'songs.seed.json'
META_JSON = BASE / 'data' / 'metadata.json'
DATE = '2026-11-27'
SONG_ID = 'verified-003'

AUDIO = 'media/thank-you-mr.mp3'
BPM = 80.0
BEATS = 4
BAR_SEC = 3.0          # 4박 × 60 / 80BPM
OFFSET = 0.04          # 녹화 4.37초 앞 무음을 잘라낸 파일의 첫 박
DURATION = 168.23      # media/thank-you-mr.mp3 길이(ffmpeg 확인)

# 실제로 울리는 코드 → (에어로밴드 14버튼, 화음 성질). Capo +4 기준.
BTN = {
    'G#m': ('Em', 'min'),
    'F#': ('D', 'maj'),
    'B': ('G', 'maj'),
    'E': ('C', 'maj'),
    'D#m': ('Bm', 'min'),
    'C#m': ('Am', 'min'),
}

SECTIONS = [
    ('도입 · 0:00–0:06', [['G#m'], ['G#m']]),
    ('1절 · 0:06–0:30', [['G#m'], ['F#', 'B'], ['G#m'], ['F#', 'B'],
                        ['G#m'], ['F#', 'B'], ['G#m'], ['G#m']]),
    ('2절 · 0:30–0:54', [['G#m'], ['G#m'], ['G#m', 'E'], ['F#', 'B'],
                        ['G#m', 'E'], ['F#', 'B'], ['G#m', 'E'], ['F#', 'B']]),
    ('간주 1 · 0:54–1:00', [['G#m', 'E'], ['E']]),
    ('후렴 1 · 1:00–1:24', [['B'], ['E'], ['B'], ['E'], ['B'], ['E'], ['D#m'], ['C#m']]),
    ('간주 2 · 1:24–1:30', [['B'], ['E']]),
    # 이 녹음은 3절도 후렴과 같은 코드(B–E–B–E–B–E–D#m–C#m) 위에 노래한다(실측).
    ('3절 · 1:30–1:54', [['B'], ['E'], ['B'], ['E'], ['B'], ['E'], ['D#m'], ['C#m']]),
    ('후렴 2 · 1:54–2:18', [['B'], ['E'], ['B'], ['E'], ['B'], ['E'], ['D#m'], ['C#m']]),
    ('후렴 3 · 2:18–2:42', [['B'], ['E'], ['B'], ['E'], ['B'], ['E'], ['D#m'], ['C#m']]),
    ('아웃트로 · 2:42–2:48', [['B'], ['B']]),
]

# (구간, 시작 마디, 가사, 차지하는 마디 수)
LYRICS = [
    ('1절', 3, "My tea's gone cold, I'm wondering why", 1),
    ('1절', 4, 'I got out of bed at all', 1),
    ('1절', 5, 'The morning rain clouds up my window', 1),
    ('1절', 6, "And I can't see at all", 1),
    ('1절', 7, "And even if I could, it'd all be gray", 1),
    ('1절', 8, 'But your picture on my wall', 1),
    ('1절', 9, "It reminds me that it's not so bad", 1),
    ('1절', 10, "It's not so bad", 1),
    ('2절', 11, 'I drank too much last night, got bills to pay', 1),
    ('2절', 12, 'My head just feels in pain', 1),
    ('2절', 13, "I missed the bus and there'll be hell today", 1),
    ('2절', 14, "I'm late for work again", 1),
    ('2절', 15, "And even if I'm there, they'll all imply", 1),
    ('2절', 16, 'That I might not last the day', 1),
    ('2절', 17, 'And then you call me', 1),
    ('2절', 18, "And it's not so bad, it's not so bad", 1),
    ('후렴 1', 21, 'And I want to thank you', 2),
    ('후렴 1', 23, 'For giving me the best day of my life', 2),
    ('후렴 1', 25, 'Oh, just to be with you', 2),
    ('후렴 1', 27, 'Is having the best day of my life', 2),
    ('3절', 31, "Push the door, I'm home at last", 1),
    ('3절', 32, "And I'm soaking through and through", 1),
    ('3절', 33, 'Then you handed me a towel', 1),
    ('3절', 34, 'And all I see is you', 1),
    ('3절', 35, 'And even if my house falls down now', 1),
    ('3절', 36, "I wouldn't have a clue", 1),
    ('3절', 37, "Because you're near me", 2),
    ('후렴 2', 39, 'And I want to thank you', 2),
    ('후렴 2', 41, 'For giving me the best day of my life', 2),
    ('후렴 2', 43, 'Oh, just to be with you', 2),
    ('후렴 2', 45, 'Is having the best day of my life', 2),
    ('후렴 3', 47, 'And I want to thank you', 2),
    ('후렴 3', 49, 'For giving me the best day of my life', 2),
    ('후렴 3', 51, 'Oh, just to be with you', 2),
    ('후렴 3', 53, 'Is having the best day of my life', 2),
]


def load_seed():
    txt = SEED_JS.read_text(encoding='utf-8')
    i = txt.index('window.STRUM_SEED')
    raw = txt[txt.index('=', i) + 1:]
    k = len(raw) - len(raw.lstrip())
    seed, end = json.JSONDecoder().raw_decode(raw[k:])
    return seed, raw[k + end:]


def save_seed(seed, tail):
    SEED_JS.write_text('window.STRUM_SEED = '
                       + json.dumps(seed, ensure_ascii=False, separators=(',', ':')) + tail,
                       encoding='utf-8')


def bar_start(bar):
    return round(OFFSET + (bar - 1) * BAR_SEC, 2)


def build_sections():
    out, n = [], 0
    for name, bars in SECTIONS:
        cells_bars = []
        for bar in bars:
            cells = []
            for chord in bar:
                btn, quality = BTN[chord]
                cells.append({'btn': btn, 'slot': 0, 'sound': chord, 'orig': chord, 'quality': quality})
            cells_bars.append(cells)
            n += 1
        out.append({'name': name, 'bars': cells_bars})
    assert n == 56, n
    return out


def build_timing():
    times = [[round(bar_start(i + 1), 2), round(bar_start(i + 1) + BAR_SEC, 2)] for i in range(56)]
    assert times[-1][1] <= DURATION + 1.0, times[-1]
    return {
        'date': DATE,
        'timeSignature': '4/4',
        'beats': BEATS,
        'bars': 56,
        'bpm': BPM,
        'audio': AUDIO,
        'durationSec': DURATION,
        'mode': 'recording',
        'source': '녹화 음원 실측(80.0BPM·4/4·첫 박 0.04초)',
        'barSec': BAR_SEC,
        'offsetSec': OFFSET,
        'barTimes': times,
        'cycle': False,
        'note': ('주성 님이 보낸 2:52 화면 녹화(Sam Backing Tracks · Acoustic Karaoke)에서 뽑은 반주로 '
                 '마디 56개의 시작·끝 시각을 실측했습니다. 80.0BPM · 4/4 · 첫 박 0.04초, 1마디 3.00초.'),
    }


def build_lyrics():
    lines = []
    for section, bar, text, span in LYRICS:
        start = bar_start(bar)
        lines.append({
            'section': section,
            'bar': bar,
            'startSec': start,
            'endSec': round(start + span * BAR_SEC, 2),
            'text': text,
        })
    # 시각이 겹치거나 뒤로 가지 않는지 확인
    for a, b in zip(lines, lines[1:]):
        assert a['endSec'] <= b['startSec'] + 0.01, (a, b)
    return {
        'version': DATE,
        'language': 'en',
        'source': '영상 자막(1절 0:10.5 · 2절 0:34.0 · 후렴 1:03.7 · 3절 1:33.6 · 후렴 1:57.0) + 마디 그리드',
        'note': ('가사 줄은 영상에 표시된 구간 순서를 이 녹화의 마디(절 1줄=1마디, 후렴 1줄=2마디)에 맞춘 '
                 '연습용 시각입니다. 노래 호흡에 따라 1초 안쪽으로 다를 수 있습니다.'),
        'lines': lines,
    }


def main():
    write = '--write' in sys.argv
    seed, tail = load_seed()
    songs = seed['songs']
    song = next(s for s in songs if s['id'] == SONG_ID)
    chart = song['chart']

    sections = build_sections()
    timing = build_timing()
    lyrics = build_lyrics()

    chart.update({
        'status': 'ready',
        'timeSignature': '4/4',
        'timeNote': '녹화 실측(80.0BPM · 4/4)',
        'bpm': int(BPM),
        'bpmNote': '녹화 음원 실측 80.0BPM (공개 코드표 표기 79~80)',
        'originalKey': 'B',
        'maleKey': 'B',
        'maleShift': 0,
        'capo': 4,
        'formButton': 'G',
        'formKey': 'B',
        'formText': 'G폼 · Capo +4',
        'sections': sections,
        'slots': [],
        'coverage': {'mapped': 6, 'total': 6, 'unmapped': 0},
        'stage': 1,
        'stroke': '↓ · ↓ ↑ · ↑ ↓ ↑ (8분 스트럼, 마디마다 코드 1개 — 마디 안에서 코드가 바뀌는 곳은 2박씩)',
        'percussive': '1절은 손바닥 뮤트로 조용히, 후렴 진입(1:00)에 맞춰 2·4박 바디 톡.',
        'why': ('B–E–B–E–B–E–D#m–C#m 후렴과 G#m–F#–B 1절이 모두 14버튼 안에서 끝나고, '
                '4/4 8비트에 한 마디 한 코드라 오른손을 처음 익히기에 가장 좋다.'),
        'basis': ('주성 님이 2026-11-27 보낸 2:52 화면 녹화(Sam Backing Tracks · Thank You - Dido Acoustic Karaoke)에서 '
                  '오디오를 뽑아 80.0BPM · 4/4 · 56마디를 실측하고, 마디마다 베이스 음·크로마로 코드를 확인했습니다. '
                  '공개 코드표(chordharbor — B장조, G폼 Capo 4, 절 Em D Em D Em D Em Em / 후렴 G C G C G C Bm Am)와 '
                  '같은 조·같은 진행입니다. 이 녹음은 3절도 후렴과 같은 코드(B–E–B–E–B–E–D#m–C#m) 위에 노래합니다. '
                  '마디 안에서 코드가 바뀌는 곳(1·2절 F#→B, G#m→E)은 2박씩 두 칸으로 표시했습니다. '
                  '실제로 울리는 코드 6개가 모두 14버튼에 들어가 손으로 잡을 코드는 없습니다.'),
        'chartNote': ('악보를 이 녹화에 맞춰 도입~아웃트로 56마디로 다시 세웠습니다(이전 10마디 연습용 배치). '
                      '마디 시각·가사 싱크는 아래 타임라인과 같습니다.'),
        'evidence': (chart.get('evidence') or []) + [
            {'label': '녹화 음원(Sam Backing Tracks · Thank You - Dido Acoustic Karaoke)',
             'url': 'https://www.youtube.com/watch?v=DwI1pUessh8',
             'note': '주성 님 2026-11-27 녹화 2:52 — 이 영상에서 반주만 뽑아 media/thank-you-mr.mp3(168.23초, -16.8 LUFS)로 넣었습니다.'},
        ],
        'timing': timing,
    })

    song.update({
        'lyrics': lyrics,
        'mrUrl': '',
        'mrAudioUrl': AUDIO,
        'mrSource': 'user-recording',
        'mrTitle': 'Thank You - Dido (Acoustic Karaoke) · Sam Backing Tracks (녹화)',
        'mrChannel': 'Sam Backing Tracks',
        'mrNote': ('2026-11-27 주성 님 녹화(2:52)에서 오디오만 추출 · 80.0BPM·4/4·56마디 실측 · '
                   '-16.8 LUFS MP3(media/thank-you-mr.mp3) · 영상 자막으로 전곡 가사 35줄 연결'),
        'bpm': int(BPM),
        'notes': ((song.get('notes') or '').split(' / 2026-11-27')[0] +
                  ' / 2026-11-27: 주성 님 녹화(2:52, Sam Backing Tracks Acoustic Karaoke) 반주를 media/thank-you-mr.mp3로 연결, '
                  '악보를 56마디 전곡으로 재구성(80.0BPM·B장조·Capo +4), 영상 자막에서 전곡 가사 35줄을 마디에 매핑.'),
    })

    # 시드 버전 · 메타 갱신
    old_ver = int(seed['meta'].get('seedVersion') or 28)
    seed['meta']['seedVersion'] = old_ver + 1
    meta = json.loads(META_JSON.read_text(encoding='utf-8'))
    meta['seedVersion'] = seed['meta']['seedVersion']

    charts = [s for s in songs if (s.get('chart') or {}).get('sections')]
    modes = Counter(s['chart']['timing']['mode'] for s in charts)
    ct = meta.get('chartTiming') or {}
    ct.update({
        'date': DATE,
        'chartCount': len(charts),
        'modes': dict(modes),
        'recording': [s['id'] for s in charts if s['chart']['timing']['mode'] == 'recording'],
        'estimated': [s['id'] for s in charts if s['chart']['timing']['mode'] == 'bpm-yt'],
        'note': ('마디 타임스탬프는 ① 녹화 음원 실측(recording) → ② 섹션 실측 구간(section) → '
                 '③ 저장소 음원 길이·첫 박(bpm-local) → ④ 유튜브 추정(bpm-yt) 순으로 채웠습니다.'),
    })
    meta['chartTiming'] = ct
    meta['lyrics'] = {
        'date': DATE,
        'songs': [s['id'] for s in songs if (s.get('lyrics') or {}).get('lines')],
        'lineCount': sum(len(s['lyrics']['lines']) for s in songs if (s.get('lyrics') or {}).get('lines')),
        'note': '가사 타임라인은 영상 자막 구간 + 마디 그리드 기준입니다(1초 안쪽 오차 가능).',
    }

    print(f"seedVersion {old_ver} → {seed['meta']['seedVersion']}")
    print(f"sections {len(sections)} · bars {sum(len(x['bars']) for x in sections)} · "
          f"lyrics {len(lyrics['lines'])}줄 · mode {timing['mode']}")
    print(f"modes {dict(modes)}")
    print(f"마디 1 {timing['barTimes'][0]} … 마디 56 {timing['barTimes'][-1]} / duration {DURATION}")

    if write:
        save_seed(seed, tail)
        SEED_JSON.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        META_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('written')
    else:
        print('(dry run — --write 로 반영)')


if __name__ == '__main__':
    main()
