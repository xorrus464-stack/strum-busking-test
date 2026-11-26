#!/usr/bin/env python3
"""stage 1(입문) 곡의 오른손 주법 → data/lessons.json 강좌 자동 매칭 (2026-11-27).

곡의 `strumming`/`stroke` 문구를 분석해 오른손 주법 강좌를 붙인다.
  1) '칼립소'                         → calypso  (칼립소 주법)
  2) '16비트'                         → beat16   (16비트 스트로크)
  3) '고고'(슬로우 고고 포함)          → gogo     (고고 · 슬로우 고고)
  4) '2·4박' 액센트                    → gogo
  5) '아르페지오'/'핑거'               → arpeggio
  6) '8비트'/'8분'/'8분음표'           → beat8    (8비트 기본 스트로크)
  7) 주법 단서가 없으면               → stroke   (스트로크 기초)

매칭 결과는 `chart.lessonKey` · `chart.lessonMatch{key,matched,confidence}` 에 넣고,
화면에서는 [▶ 이 곡 오른손 주법 배우기] 버튼으로 해당 강좌 영상을 미니 플레이어에서 재생한다.
stage 1 곡만 대상으로 한다(계획서 범위).

실행: python3 tools/apply_rhythm_lesson_2026_11_27.py [--write]
"""
import json
import pathlib
import sys
from collections import Counter

BASE = pathlib.Path(__file__).resolve().parents[1]
SEED_JS = BASE / 'src' / 'seed.js'
SEED_JSON = BASE / 'data' / 'songs.seed.json'
DATE = '2026-11-27'

RULES = [
    ('calypso', ('칼립소',)),
    ('beat16', ('16비트', '16분')),
    ('gogo', ('고고', '2·4박', '2,4박', '2-4박', '2·4')),
    ('arpeggio', ('아르페지오', '핑거')),
    ('beat8', ('8비트', '8분')),
]
FALLBACK = 'stroke'


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


def match(text):
    t = str(text or '')
    for key, words in RULES:
        for w in words:
            if w in t:
                return key, w, '문구 일치'
    return FALLBACK, '', '주법 단서 없음 → 기본'


def main():
    write = '--write' in sys.argv
    seed, tail = load_seed()
    lessons = json.loads((BASE / 'data' / 'lessons.json').read_text(encoding='utf-8'))['lessons']
    by_key = {l['key']: l for l in lessons}
    songs = seed['songs']
    stage1 = [s for s in songs if isinstance(s.get('chart'), dict)
              and s['chart'].get('sections') and s['chart'].get('stage') == 1]
    counts = Counter()
    rows = []
    for s in stage1:
        c = s['chart']
        text = ' '.join(x for x in (c.get('stroke'), s.get('strumming')) if x)
        key, hit, conf = match(text)
        c['lessonKey'] = key
        c['lessonMatch'] = {'key': key, 'name': by_key[key]['name'], 'matched': hit,
                            'confidence': conf, 'from': text[:90], 'date': DATE}
        counts[key] += 1
        rows.append((s['id'], s['title'][:30], c.get('timeSignature'), c.get('bpm'), key, hit or '-', text[:52]))
    print(f'stage 1 악보 {len(stage1)}곡 · 매칭 {dict(counts)}')
    for r in rows:
        print(f'  {r[0]:16s} {r[1]:32s} {r[2]:4s} {str(r[3]):4s} → {r[4]:9s} ({r[5]})  {r[6]}')
    assert set(counts) <= set(by_key), counts
    assert all(s['chart']['lessonKey'] in by_key for s in stage1)
    if write:
        meta = seed['meta']
        meta['rhythmLesson'] = {
            'date': DATE,
            'stage1Songs': len(stage1),
            'counts': dict(counts),
            'rules': '칼립소→calypso · 16비트→beat16 · 고고/2·4박→gogo · 아르페지오→arpeggio · 8비트/8분→beat8 · 단서 없음→stroke',
            'note': 'stage 1(입문) 곡의 오른손 주법 문구를 강좌에 연결했습니다. 다른 단계 곡은 기존처럼 스트로크 표기만 보여줍니다.',
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
