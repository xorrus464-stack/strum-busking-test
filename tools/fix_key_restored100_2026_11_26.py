#!/usr/bin/env python3
"""restored-100 「Good Bye-Bye (グッバイバイ)」 악보 키 정정 — 2026-11-26

왜 고치는가
- 이 곡의 원곡 조성은 **B♭장조**로 확인됐습니다.
  · 유튜브 공식 MV/음원: kokomu 코드표 B♭長調 4/4 · 악보바다 원키 Bb · ChordU In Key Bb(코드 F·E♭·Gm·B♭·Dm)
  · KeyTube 음역 F3~C5, 최빈음 A♯4 (B♭장조의 으뜸음)
  · 주성 님이 2026-11-24에 올린 반주 녹화(`attachments/2026-11-24/1000034386-*.mp4`) 실측:
    마지막 6초 크로마 A♯ 0.99 · 저음 루트 A♯ 0.40 → 곡이 B♭으로 끝남(으뜸음 B♭)
- 그런데 seed 에는 원곡 키가 **C**로 잘못 들어가 있었고(코드표를 C로 적은 웹 자료를 그대로 옮김),
  남자키 -5반음이 그 C에 적용되어 악보가 **G장조**로 울렸습니다.
- 실제 반주 파일 `media/goodbye-bye-mr.mp3` 는 원본 녹화에서 **정확히 -5반음** = **F장조**입니다.
  (원본↔MP3 크로마 회전 상관 0.9948 @ -5반음, MP3 마지막 6초 저음 루트 F)
- 결과적으로 **악보(G)가 반주(F)보다 2반음 높아** 반주에 맞춰 치면 어긋났습니다.

고치는 내용
- 악보를 반주와 같은 **F장조**로 내립니다. 버튼(폼)은 F·G·Em·Am 그대로 두고 **Capo 2 → 0**.
  (F폼 + Capo 0 = F·G·Em·Am / 14버튼 안에서 슬롯 0개로 완주. Capo 2는 D·E·C#m·F#m 이 되어 버튼에 없습니다.)
- 원곡 키 표기 C → B♭, 남자키 G → F, 마디별 `sound`(실제 울리는 코드)·`orig`(원곡 키 코드)를 -2반음.
- 곡 카드의 코드 문자열·설명·근거도 함께 정정.

실행: python3 tools/fix_key_restored100_2026_11_26.py [--write]
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
SHIFT = -2                     # 악보를 2반음 내린다 (G → F)
SEED_VERSION = 24              # 23 → 24, ?v= 25
CACHE_VERSION = 25

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
    if not chord:
        return chord
    root, suf = split_chord(chord)
    if root not in PC:
        return chord
    return NAME[(PC[root] + semis) % 12] + suf


NOTE = ('2026-11-26 악보 키 정정: 원곡이 B♭장조로 확인돼(원곡 음원 실측 · 공개 코드표) '
        '남자키 -5반음 = F장조로 악보·Capo를 다시 계산했습니다. 이전 악보는 C를 원곡 키로 잘못 잡아 '
        '실제 반주(F)보다 2반음 높은 G로 울렸습니다. 버튼 F·G·Em·Am 그대로 Capo 2 → 0.')


def main():
    write = '--write' in sys.argv
    songs = json.loads(SEED_JSON.read_text(encoding='utf-8'))
    target = next((s for s in songs if s.get('id') == SONG_ID), None)
    if target is None:
        raise SystemExit('restored-100 not found')

    chart = target['chart']
    print('BEFORE:', json.dumps({k: chart[k] for k in
                                 ('originalKey', 'maleKey', 'maleShift', 'capo', 'formButton', 'formKey', 'formText')},
                                ensure_ascii=False))
    print('  song key/maleKey:', target.get('key'), '/', target.get('maleKey'))

    # ① 곡 카드
    target['key'] = 'Bb'
    target['maleKey'] = 'F'
    target['chords'] = ' / '.join(
        ' '.join(transpose(c, SHIFT) for c in part.split())
        for part in str(target.get('chords', '')).split(' / ')
    )

    # ② 악보 머리
    chart['originalKey'] = 'Bb'
    chart['maleKey'] = 'F'
    chart['maleShift'] = 5
    chart['capo'] = 0
    chart['formButton'] = 'F'
    chart['formKey'] = 'Bb'
    chart['formText'] = 'F폼 · Capo +0'

    # ③ 마디별 코드 — sound(실제 울리는 코드)와 orig(원곡 키 코드)만 -2반음, 버튼은 그대로
    changed = 0
    for sec in chart.get('sections', []):
        for bar in sec.get('bars', []):
            for cell in bar:
                if not isinstance(cell, dict):
                    continue
                cell['sound'] = transpose(cell['sound'], SHIFT)
                if cell.get('orig'):
                    cell['orig'] = transpose(cell['orig'], SHIFT)
                changed += 1

    # ④ 설명·근거
    chart['why'] = ('B♭ 원곡을 -5반음 내린 F키. F·G·Em·Am 네 코드가 계속 돌아가고 모두 14버튼 안에 있어 '
                    'Capo 0에서 슬롯 없이 완주합니다.')
    chart['timeNote'] = chart.get('timeNote') or ''
    chart['bpmNote'] = chart.get('bpmNote') or ''
    ev = chart.get('evidence') or []
    ev.append({'label': '원곡 조성 실측(주성 님 2026-11-24 반주 녹화)',
               'url': 'https://youtu.be/i7kRQsCIvv0',
               'note': 'B♭장조 — 마지막 6초 크로마 A♯ 0.99 · 저음 루트 A♯ 0.40 (kokomu B♭長調 · ChordU Key Bb 와 일치)'})
    chart['evidence'] = ev
    chart['keyNote'] = NOTE
    if isinstance(chart.get('shapeInfo'), dict):
        chart['shapeInfo']['capo'] = 0
    if isinstance(chart.get('remap'), dict):
        chart['remap']['capoTo'] = 0
        chart['remap']['keyFix'] = '2026-11-26 G → F (Capo 2 → 0)'
    target['chartNote'] = NOTE

    print('AFTER :', json.dumps({k: chart[k] for k in
                                 ('originalKey', 'maleKey', 'maleShift', 'capo', 'formButton', 'formKey', 'formText')},
                                ensure_ascii=False))
    print(f'  마디 코드 {changed}개 -2반음 · 코드 문자열:')
    print('  ', target['chords'][:120])
    sounds = sorted({c['sound'] for sec in chart['sections'] for bar in sec['bars'] for c in bar})
    btns = sorted({c['btn'] for sec in chart['sections'] for bar in sec['bars'] for c in bar})
    slots = chart.get('slots') or []
    print('  실제 울리는 코드:', sounds, '· 버튼:', btns, '· 슬롯:', len(slots))

    if not write:
        print('\n(미리보기) --write 를 붙이면 반영합니다.')
        return

    SEED_JSON.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    meta = json.loads(META_JSON.read_text(encoding='utf-8'))
    meta['seedVersion'] = SEED_VERSION
    meta['chartDisclosure'] = str(meta.get('chartDisclosure', '')) + ' ' + NOTE
    META_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    sources = json.loads((BASE / 'data' / 'source-videos.seed.json').read_text(encoding='utf-8'))
    payload = {'songs': songs, 'sources': sources, 'meta': meta}
    SEED_JS.write_text('window.STRUM_SEED = ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n',
                       encoding='utf-8')

    for name in ('index.html', 'src/app.js', 'src/styles.css'):
        p = BASE / name
        t = p.read_text(encoding='utf-8')
        t2 = re.sub(r'\?v=\d+', f'?v={CACHE_VERSION}', t)
        p.write_text(t2, encoding='utf-8')
        print(f'{name}: ?v={CACHE_VERSION}')

    sw = BASE / 'sw.js'
    t = sw.read_text(encoding='utf-8')
    t2 = re.sub(r"strum-busking-test-v\d+", f'strum-busking-test-v{CACHE_VERSION}', t)
    sw.write_text(t2, encoding='utf-8')
    print(f'sw.js: cache v{CACHE_VERSION}')

    print(f'OK · seedVersion {SEED_VERSION} · 캐시 v{CACHE_VERSION}')


if __name__ == '__main__':
    main()
