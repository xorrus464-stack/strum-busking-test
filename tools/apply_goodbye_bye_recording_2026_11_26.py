#!/usr/bin/env python3
"""restored-100 「Good Bye-Bye (グッバイバイ)」 — 2026-11-26 주성 님 녹화 음원 반영

무엇을 하는가
1) 주성 님이 보낸 화면 녹화(DCS | Dallas Cover Studio 남자 커버, 4분 11초)에서 뽑은
   풀트랙(media/goodbye-bye-full.mp3)과 기타를 살린 MR(media/goodbye-bye-mr.mp3)을 곡에 연결한다.
2) 녹음 실측(2026-11-26): B♭장조 · 89.10bpm · 4/4 — 원곡과 같은 조.
   이전 악보는 -5반음 F장조(F폼 Capo 0)라 이 녹음보다 5반음 낮았다.
   → 악보를 이 녹음 키 B♭로 다시 세팅: C폼 · Capo +3 (C·D·Bm·Em·G 버튼 = E♭·F·Dm·Gm·B♭, 슬롯 0)
3) 마디 카드는 공개 코드표(GuitarTabsExplorer, Capo 3 · Key C — Cadd9·Dsus·Bm·Em·G)의
   진행을 4박 마디로 정리하고, 녹음 실측 코드 어휘(B♭·E♭·F·Gm·Dm·Cm)와 맞는지 확인했다.

실행: python3 tools/apply_goodbye_bye_recording_2026_11_26.py [--write]
      --write 없이 실행하면 바뀔 내용만 보여줍니다.
"""
import json
import re
import sys
import pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
SEED_JS = BASE / 'src' / 'seed.js'
SEED_JSON = BASE / 'data' / 'songs.seed.json'
META_JSON = BASE / 'data' / 'metadata.json'
SONG_ID = 'restored-100'
SEED_VERSION = 25              # 24 → 25, ?v= 26
CACHE_VERSION = 26

CAPO = 3
PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6,
      'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
NAME = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']


def split_chord(chord):
    t = str(chord).split('/')[0].strip()
    i = 1
    while i < len(t) and t[i] in '#b':
        i += 1
    return t[:i], t[i:]


def transpose(chord, semis):
    root, suf = split_chord(chord)
    if root not in PC:
        return chord
    return NAME[(PC[root] + semis) % 12] + suf


# (섹션 이름, [마디별 버튼 목록]) — 버튼은 에어로밴드 원터치 14버튼 이름
SECTIONS = [
    ('Intro', [['C', 'D'], ['Bm', 'Em'], ['C', 'D'], ['Bm', 'Em']]),
    ('Verse', [['C', 'D'], ['Bm', 'Em'], ['C', 'D'], ['Bm', 'Em']]),
    ('Pre', [['C', 'Em'], ['G', 'D'], ['C', 'Em'], ['G', 'D']]),
    ('Chorus', [['C', 'D'], ['Bm', 'Em'], ['C', 'D'], ['G'],
                ['C', 'D'], ['Bm', 'Em'], ['C', 'D'], ['G']]),
    ('Bridge', [['C'], ['Em'], ['C', 'Em'], ['D'], ['C'], ['G']]),
    ('Outro', [['C', 'D'], ['G']]),
]

NOTE = ('2026-11-26 녹화 음원 반영: 주성 님이 보낸 화면 녹화(DCS | Dallas Cover Studio 남자 커버, 4분 11초)에서 '
        '오디오를 뽑아 실측한 결과 이 녹음은 **B♭장조 · 89.10bpm · 4/4**입니다(원곡과 같은 조). '
        '그래서 악보를 이 녹음에 맞춰 B♭로 올렸습니다 — 버튼 C·D·Bm·Em·G(14버튼)에 Capo +3, 실제로 울리는 코드는 '
        'E♭·F·Dm·Gm·B♭이고 손으로 잡을 코드는 0개입니다. 이전 악보(F장조 · F폼 Capo 0)는 이 녹음보다 5반음 낮아 '
        '반주에 맞춰 치면 조가 어긋났습니다.')

WHY = ('이 녹음은 B♭장조라서 C폼에 Capo +3을 대면 C·D·Bm·Em·G 다섯 버튼이 E♭·F·Dm·Gm·B♭로 울립니다. '
       '곡에 나오는 코드가 모두 14버튼 안에 있어 Capo +3에서 슬롯 없이 끝까지 칩니다.')

FULL_NOTE = ('주성 님 2026-11-26 화면 녹화에서 오디오만 추출(앞 4.0초 무음·끝 페이드 정리, 길이·템포 그대로) · '
             'media/goodbye-bye-full.mp3 (5.9MB · 4분 6.6초 · 192kbps · -17.2 LUFS) · '
             '같은 녹화에서 만든 MR과 같은 키(B♭장조)')

MR_NOTE = ('주성 님 2026-11-26 화면 녹화(유튜브 DCS | Dallas Cover Studio 「【グッバイバイ】冨岡愛 - Intimate Acoustic Pop '
           '(Male Cover)」 · 4분 11초)에서 오디오만 추출 → UVR MDX-NET Inst_HQ_5로 보컬 분리 + 기타 보존 후처리'
           '(보컬이 없는 구간은 원음 그대로, 4.5kHz 이상은 보컬을 55%만 제거해 기타의 밝기 유지) · '
           '실측 B♭장조 89.10bpm · media/goodbye-bye-mr.mp3 (5.9MB · 4분 6.6초 · 192kbps · -17.2 LUFS) · '
           '미니 플레이어에서 바로 재생, -6~+6반음 실시간 키 조절(템포 유지)')


def main():
    write = '--write' in sys.argv
    songs = json.loads(SEED_JSON.read_text(encoding='utf-8'))
    target = next((s for s in songs if s.get('id') == SONG_ID), None)
    if target is None:
        raise SystemExit('restored-100 not found')
    chart = target['chart']

    # ① 곡 카드
    target['key'] = 'Bb'
    target['maleKey'] = 'Bb'
    target['bpm'] = 89
    target['chordStatus'] = '웹 자료 검수 완료'
    target['strumming'] = '↓ ↓↑ ↑↓ ↑ (8분 스트럼, 89bpm)'

    # ② 악보 머리
    chart['timeSignature'] = '4/4'
    chart['timeNote'] = '녹음 실측 4/4 (89.10bpm)'
    chart['bpm'] = 89
    chart['bpmNote'] = '녹음 실측 89.10bpm (2026-11-26)'
    chart['originalKey'] = 'Bb'
    chart['maleKey'] = 'Bb'
    chart['maleShift'] = 0
    chart['capo'] = CAPO
    chart['formButton'] = 'C'
    chart['formKey'] = 'Bb'
    chart['formText'] = 'C폼 · Capo +3'

    # ③ 마디 카드 (버튼·실제 울리는 코드·원곡 키 코드)
    sections = []
    bars_total = 0
    for name, bars in SECTIONS:
        rows = []
        for bar in bars:
            cells = []
            for btn in bar:
                sound = transpose(btn, CAPO)
                cells.append({
                    'btn': btn,
                    'slot': 0,
                    'sound': sound,
                    'orig': sound,
                    'quality': 'min' if btn.endswith('m') and not btn.startswith('Bdim') else 'maj',
                })
            rows.append(cells)
            bars_total += 1
        sections.append({'name': name, 'bars': rows})
    chart['sections'] = sections
    chart['slots'] = []
    chart['stage'] = 1
    chart['percussiveReady'] = False
    chart['percussive'] = ''
    chart['stroke'] = '↓ ↓↑ ↑↓ ↑ (8분 스트럼, 89bpm)'
    chart['why'] = WHY
    chart['basis'] = ('공개 코드표(GuitarTabsExplorer · Capo 3 · Key C — Cadd9·Dsus·Bm·Em·G)의 절 순서를 4박 마디 카드로 '
                      '정리하고, 2026-11-26 녹화 실측 코드 어휘(B♭·E♭·F·Gm·Dm·Cm)와 맞는지 확인한 연습용 배치입니다. '
                      '원곡의 세부 마디 배치와 다를 수 있습니다.')
    used = sorted({c['btn'] for sec in sections for bar in sec['bars'] for c in bar})
    chart['coverage'] = {'mapped': len(used), 'total': len(used), 'unmapped': 0}
    chart['shapeInfo'] = {'capo': CAPO, 'chords': [],
                          'note': '14버튼만으로 완주 — 손으로 잡을 코드가 없습니다.'}
    chart['remap'] = {'btnSet': 14, 'date': '2026-11-26', 'mode': 'easy-leftover',
                      'capoFrom': 0, 'capoTo': CAPO, 'slotsFrom': 0, 'slotsTo': 0,
                      'keyFix': '2026-11-26 악보를 이 녹음 키(B♭)로 — F폼 Capo 0 → C폼 Capo +3'}
    chart['keyNote'] = NOTE
    chart['evidence'] = [
        {'label': '2026-11-26 주성 님 녹화 실측(DCS 남자 커버)',
         'url': 'https://youtu.be/aJIGwku9UlE',
         'note': 'B♭장조(보컬 스템 크로마 상관 B♭장조 0.81 · 반주 0.57) · 89.10bpm · 4/4 · '
                 '코드 어휘 B♭·E♭·F·Gm·Dm·Cm · 곡이 B♭으로 끝남'},
        {'label': 'GuitarTabsExplorer 코드표 (Capo 3 · Key C)',
         'url': 'https://www.guitartabsexplorer.com/ai-tomioka/good-bye-bye-chords',
         'note': 'Cadd9·Dsus·Bm·Em·G — Capo 3에서 E♭·F·Dm·Gm·B♭로 울려 이 녹음과 같은 폼'},
        {'label': 'kokomu · ChordU (원곡 B♭장조)', 'url': 'https://chordu.com/chords-tabs-ai-tomioka-good-bye-bye',
         'note': 'In Key Bb — 코드 F·E♭·Gm·B♭·Dm (2026-11-26 이전 조사 기록 유지)'},
        {'label': '원곡 조성 실측(주성 님 2026-11-24 반주 녹화)',
         'url': 'https://youtu.be/i7kRQsCIvv0',
         'note': 'B♭장조 — 마지막 6초 크로마 A♯ 0.99 · 저음 루트 A♯ 0.40'},
    ]
    chart['status'] = 'ready'

    # ④ 곡 카드 코드 문자열(실제 울리는 코드)
    target['chords'] = ' / '.join(' '.join(transpose(c['btn'], CAPO) for c in bar)
                                  for sec in sections for bar in sec['bars'])
    target['chartStatus'] = 'ready'
    target['chartNote'] = NOTE
    target['chartStage'] = 1

    # ⑤ 음악·MR 음원 파일
    target['fullAudioUrl'] = 'media/goodbye-bye-full.mp3'
    target['fullNote'] = FULL_NOTE
    target['mrAudioUrl'] = 'media/goodbye-bye-mr.mp3'
    target['mrTitle'] = 'Good Bye-Bye 남자 커버 반주 (기타 살린 MR) · 주성 님 녹화'
    target['mrNote'] = MR_NOTE
    target['mrSource'] = 'user-recording'
    target['mrUrl'] = ''
    target['videoStatus'] = '공개 영상(남자 커버)'
    if '2026-11-26' not in (target.get('notes') or ''):
        target['notes'] = (target.get('notes') or '') + (
            ' 2026-11-26 녹화 음원 반영: 주성 님이 보낸 화면 녹화(DCS | Dallas Cover Studio 남자 커버)에서 음악·MR을 '
            '뽑아 등록하고, 실측 키 B♭(89.10bpm)에 맞춰 악보를 C폼 Capo +3으로 다시 세팅했습니다.')

    print('BEFORE key/maleKey:', 'Bb', '/', 'F', '· capo 0 · F폼 · sound F·G·Em·Am·C')
    print('AFTER  key/maleKey:', target['key'], '/', target['maleKey'], '· capo', chart['capo'], '·', chart['formText'])
    print('  마디 %d개 · 버튼 %s · 실제 울리는 코드 %s · 슬롯 %d'
          % (bars_total, used, sorted({c['sound'] for sec in sections for bar in sec['bars'] for c in bar}), len(chart['slots'])))
    print('  음악:', target['fullAudioUrl'], '· MR:', target['mrAudioUrl'])

    if not write:
        print('\n(미리보기) --write 를 붙이면 반영합니다.')
        return

    SEED_JSON.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    meta = json.loads(META_JSON.read_text(encoding='utf-8'))
    meta['seedVersion'] = SEED_VERSION
    meta['mrVersion'] = '2026-11-26'
    meta['mrDisclosure'] = str(meta.get('mrDisclosure', '')) + ' ' + (
        'Good Bye-Bye(restored-100)는 주성 님 2026-11-26 녹화에서 뽑은 음악(media/goodbye-bye-full.mp3)과 '
        '보컬을 제거한 반주(media/goodbye-bye-mr.mp3)로 바꿨습니다(녹화 음원 분리, 실측 B♭장조 89.10bpm).')
    meta['chartDisclosure'] = str(meta.get('chartDisclosure', '')) + ' ' + NOTE
    META_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    sources = json.loads((BASE / 'data' / 'source-videos.seed.json').read_text(encoding='utf-8'))
    payload = {'songs': songs, 'sources': sources, 'meta': meta}
    SEED_JS.write_text('window.STRUM_SEED = ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n',
                       encoding='utf-8')

    for name in ('index.html', 'src/app.js', 'src/styles.css'):
        p = BASE / name
        t = p.read_text(encoding='utf-8')
        p.write_text(re.sub(r'\?v=\d+', f'?v={CACHE_VERSION}', t), encoding='utf-8')
        print(f'{name}: ?v={CACHE_VERSION}')

    sw = BASE / 'sw.js'
    t = sw.read_text(encoding='utf-8')
    sw.write_text(re.sub(r'strum-busking-test-v\d+', f'strum-busking-test-v{CACHE_VERSION}', t), encoding='utf-8')
    print(f'sw.js: cache v{CACHE_VERSION}')
    print(f'OK · seedVersion {SEED_VERSION} · 캐시 v{CACHE_VERSION}')


if __name__ == '__main__':
    main()
