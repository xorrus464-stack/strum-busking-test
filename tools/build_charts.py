#!/usr/bin/env python3
"""곡 데이터에 남자키·카포·원터치 컬러 악보·SimplifyChord 슬롯을 계산해 병합한다.

실행: python3 tools/build_charts.py
입력: data/songs.seed.json (+ tools/chart_data.py)
출력: data/songs.seed.json, data/songs.all.csv, data/songs.verified.csv, src/seed.js, data/chart-coverage.csv
"""
import csv
import json
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'tools'))
from chart_data import CHARTS, FEMALE_ORIGINAL  # noqa: E402
from collections import Counter  # noqa: E402

SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT_OF = {'D#': 'Eb', 'G#': 'Ab', 'A#': 'Bb'}
PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6,
      'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11,
      'Cb': 11, 'Fb': 4}
SHAPES = {'C': (0, 'maj'), 'D': (2, 'maj'), 'E': (4, 'maj'), 'F': (5, 'maj'), 'G': (7, 'maj'),
          'Cm': (0, 'min'), 'Dm': (2, 'min'), 'Em': (4, 'min'), 'Fm': (5, 'min'), 'Gm': (7, 'min')}
ONE_TOUCH_ORDER = ['C', 'Dm', 'Em', 'F', 'G', 'Cm', 'D', 'E', 'Fm', 'Gm']
# 원터치 버튼에 없는 코드를 슬롯에 넣을 때 흔히 쓰는 약식 대안(사실 기반 제안, 연주자 선택)
EASY_ALT = {
    'B': 'B7(x21202) 약식', 'Bm': 'Bm7(x20202)', 'Bb': 'Bb(6프렛 바레) 또는 A# 약식',
    'Bbm': 'Bbm7(x13121)', 'Am': 'Am7(x02010)', 'A': 'A(x02220)', 'F': 'Fmaj7(xx3210) 약식',
    'Fm': 'Fm7(131111) 3현만', 'C#m': 'C#m7(x46454)', 'G#': 'G#7(464544)', 'G#m': 'G#m7(464444)',
    'D#': 'D#(x68886)', 'A#m': 'A#m7(x13121)', 'Dm': 'Dm7(xx0211)', 'Cm': 'Cm7(x35343)',
    'Eb': 'Eb(x68886)', 'Ab': 'Ab(466544)', 'Db': 'Db(x46664)', 'E7': 'E7(020100)',
    'A7': 'A7(x02020)', 'G7': 'G7(320001)', 'D7': 'D7(xx0212)', 'B7': 'B7(x21202)',
    'F#': 'F#(244322)', 'F#m': 'F#m(244222)', 'Bm7': 'Bm7(x20202)', 'Am7': 'Am7(x02010)',
}


def parse_chord(text):
    t = text.strip()
    bass = ''
    if '/' in t:
        t, bass = t.split('/', 1)
    i = 1
    while i < len(t) and t[i] in '#b':
        i += 1
    root, suffix = t[:i], t[i:]
    if root not in PC:
        raise ValueError('unknown chord root: ' + text)
    quality = 'min' if (suffix.startswith('m') and not suffix.startswith('maj')) else 'maj'
    return {'root': root, 'suffix': suffix, 'quality': quality, 'text': text, 'bass': bass}


def name(pc, prefer_flat=False):
    s = SHARP[pc % 12]
    if s in FLAT_OF:
        return FLAT_OF[s]
    if prefer_flat and s == 'C#':
        return 'Db'
    return s


def shift_name(root, semis, prefer_flat):
    return name((PC[root] - semis) % 12, prefer_flat)


def find_button(root_pc, quality, capo):
    for btn in ONE_TOUCH_ORDER:
        p, q = SHAPES[btn]
        if q == quality and (p + capo) % 12 == root_pc % 12:
            return btn
    return None


def nice_key(k, prefer_flat):
    if not k:
        return ''
    b = parse_chord(k)
    return name(PC[b['root']], prefer_flat) + ('m' if b['quality'] == 'min' else '')


def ideal_shift(sid):
    return 4 if sid in FEMALE_ORIGINAL else 2


def plan(sid, data):
    """(shift, capo)를 골라 원터치 버튼에 가장 많이 들어가는 조합을 찾는다."""
    orig = data['originalKey']
    prefer_flat = 'b' in orig or orig in ('F',)
    chords = []
    for sec in data['sections']:
        for bar in sec['bars']:
            for c in bar:
                chords.append(c)
    uniq = list(dict.fromkeys(chords))
    weight = Counter(chords)
    parsed = [(c, parse_chord(c)) for c in uniq]
    ideal = ideal_shift(sid)
    best = None
    for shift in range(0, 7):
        if abs(shift - ideal) > 2:
            continue
        male = {c: shift_name(p['root'], shift, prefer_flat) + p['suffix'] for c, p in parsed}
        male_pc = {c: PC[shift_name(p['root'], shift, prefer_flat)] for c, p in parsed}
        for capo in range(0, 8):
            mapped = sum(1 for c, p in parsed if find_button(male_pc[c], p['quality'], capo))
            unmapped = len(parsed) - mapped
            mapped_occ = sum(weight[c] for c, p in parsed if find_button(male_pc[c], p['quality'], capo))
            tonic = parse_chord(orig)
            tonic_ok = find_button((PC[tonic['root']] - shift) % 12, tonic['quality'], capo) is not None
            # ① 슬롯(원터치에 없는 코드) 수를 가장 작게 ② 카포는 낮게 ③ 남자키는 기본값에 가깝게
            # ① 슬롯 수 최소 ② 남자키는 보컬 기준값 유지 ③ 카포는 낮은 쪽
            score = (-unmapped * 1000 - abs(shift - ideal) * 40 - capo * 3
                     + (15 if capo <= 5 else 0) + (30 if tonic_ok else 0) + mapped_occ * 0.5)
            if best is None or score > best[0]:
                best = (score, shift, capo, mapped, unmapped, male, male_pc)
    _, shift, capo, mapped, unmapped, male, male_pc = best
    return {
        'shift': shift, 'capo': capo, 'prefer_flat': prefer_flat,
        'male': male, 'male_pc': male_pc, 'mapped': mapped, 'unmapped': unmapped,
        'total': len(parsed), 'ideal': ideal,
    }


def build_chart(sid, data):
    org = data['originalKey']
    p = plan(sid, data)
    sections = []
    slot_map = {}
    slot_list = []
    for sec in data['sections']:
        bars = []
        for bar in sec['bars']:
            cells = []
            for c in bar:
                pc_ = parse_chord(c)
                male_chord = p['male'][c]
                btn = find_button(p['male_pc'][c], pc_['quality'], p['capo'])
                if btn is None:
                    if c not in slot_map:
                        if len(slot_list) >= 5:
                            slot_map[c] = 0
                        else:
                            slot_list.append(c)
                            slot_map[c] = len(slot_list)
                    cells.append({'btn': None, 'slot': slot_map[c], 'sound': male_chord,
                                  'orig': c, 'quality': pc_['quality']})
                else:
                    cells.append({'btn': btn, 'slot': 0, 'sound': male_chord,
                                  'orig': c, 'quality': pc_['quality']})
            bars.append(cells)
        sections.append({'name': sec['name'], 'bars': bars})
    slots = []
    for i, c in enumerate(slot_list, 1):
        q = parse_chord(c)
        slots.append({
            'slot': i,
            'chord': p['male'][c],
            'orig': c,
            'alt': EASY_ALT.get(p['male'][c], EASY_ALT.get(c, '')),
            'why': '원터치 10버튼에 없는 코드(바레/전위 등)',
        })
    male_key = name((PC[parse_chord(org)['root']] - p['shift']) % 12, p['prefer_flat'])
    if parse_chord(org)['quality'] == 'min':
        male_key += 'm'
    ton = parse_chord(org)
    tonic_btn = find_button((PC[ton['root']] - p['shift']) % 12, ton['quality'], p['capo'])
    stage = data.get('stage')
    if stage is None:
        stage = 1 if p['total'] <= 4 else (2 if p['total'] <= 6 and len(slots) <= 1 else 3)
    chart = {
        'status': 'ready',
        'timeSignature': data['timeSignature'],
        'timeNote': data.get('timeNote', ''),
        'bpm': data['bpm'],
        'bpmNote': data.get('bpmNote', ''),
        'originalKey': nice_key(org, p['prefer_flat']),
        'maleKey': male_key,
        'maleShift': p['shift'],
        'capo': p['capo'],
        'formButton': tonic_btn or '',
        'formKey': name(p['capo'] % 12, p['prefer_flat']),
        'formText': (f"{tonic_btn}폼 · Capo +{p['capo']}" if tonic_btn else f"Capo +{p['capo']}"),
        'sections': sections,
        'slots': slots,
        'stage': stage,
        'percussiveReady': bool(data.get('percussiveReady')) or stage == 4,
        'stroke': data.get('stroke', ''),
        'percussive': data.get('percussive', ''),
        'why': data.get('why', ''),
        'coverage': {'mapped': p['mapped'], 'total': p['total'], 'unmapped': p['unmapped']},
        'basis': '코드표 순서를 4박 마디 카드로 정리한 연습용 배치입니다. 원곡의 세부 마디 배치와 다를 수 있습니다.',
        'evidence': [{'label': a, 'url': b, 'note': c} for a, b, c in data.get('evidence', [])],
    }
    return chart, male_key


def main():
    songs = json.loads((BASE / 'data' / 'songs.seed.json').read_text(encoding='utf-8'))
    sources = json.loads((BASE / 'data' / 'source-videos.seed.json').read_text(encoding='utf-8'))
    meta = json.loads((BASE / 'data' / 'metadata.json').read_text(encoding='utf-8'))
    by_id = {s['id']: s for s in songs}
    coverage_rows = []
    ready = partial = pending = 0
    for s in songs:
        data = CHARTS.get(s['id'])
        if not data:
            if s.get('chart'):
                del s['chart']
            s['chartStatus'] = 'pending'
            s['chartNote'] = '코드·키·박자 확인 전 — 검수 대기'
            continue
        if data.get('missing'):
            s['chartStatus'] = 'pending'
            s['chartNote'] = data['missing']
            s.pop('chart', None)
            pending += 1
            continue
        if 'sections' not in data:
            chart = {
                'status': 'partial',
                'timeSignature': data.get('timeSignature', ''),
                'timeNote': data.get('timeNote', ''),
                'bpm': data.get('bpm', 0),
                'bpmNote': data.get('bpmNote', ''),
                'originalKey': data.get('originalKey', ''),
                'maleKey': '', 'maleShift': data.get('shift', 0), 'capo': None,
                'formButton': '', 'formKey': '', 'formText': '',
                'sections': [], 'slots': [], 'stage': 3, 'stroke': '', 'percussive': '',
                'why': '', 'coverage': {'mapped': 0, 'total': 0, 'unmapped': 0},
                'basis': '', 'note': data.get('partial', ''), 'evidence': [],
            }
            s['chart'] = chart
            s['chartStatus'] = 'partial'
            s['chartNote'] = data.get('partial', '')
            s['key'] = chart['originalKey']
            s['bpm'] = chart['bpm'] or None
            s['timeSignature'] = chart['timeSignature']
            s['chordStatus'] = '부분 확인'
            partial += 1
            continue
        chart, male_key = build_chart(s['id'], data)
        if data.get('partial'):
            chart['status'] = 'partial'
            chart['note'] = data['partial']
            s['chartStatus'] = 'partial'
            partial += 1
        else:
            s['chartStatus'] = 'ready'
            ready += 1
        s['chart'] = chart
        s['chartNote'] = data.get('partial', '')
        s['key'] = chart['originalKey']
        s['maleKey'] = male_key
        s['bpm'] = chart['bpm'] or None
        s['chordStatus'] = '웹 자료 검수 완료' if chart['status'] == 'ready' else '부분 확인'
        s['strumming'] = chart['stroke']
        s['chords'] = ' / '.join(
            ' '.join(c['orig'] for c in bar) for sec in chart['sections'] for bar in sec['bars']
        )[:400]
        s['timeSignature'] = chart['timeSignature']
        s['chartStage'] = chart.get('stage')
        s['tags'] = [t for t in (s.get('tags') or []) if t in ('입문 후보', '연습 추천곡')]
        if chart['status'] == 'ready' and s['chartStage'] == 1 and '오른손 1단계' not in s['tags']:
            s['tags'].append('오른손 1단계')
        coverage_rows.append([s['id'], s['title'], s['artist'], chart['originalKey'], male_key,
                              chart['capo'], chart['formText'], chart['timeSignature'], chart['bpm'],
                              chart['coverage']['mapped'], chart['coverage']['total'],
                              len(chart['slots']), chart['stage'], chart['status']])
    meta['seedVersion'] = 4
    meta['chartVersion'] = '2026-11-22'
    meta['chartReadyCount'] = ready
    meta['chartPartialCount'] = partial
    meta['chartPendingCount'] = pending
    meta['chartDisclosure'] = (
        f'남자키·박자·BPM·코드 진행은 2026-11-22 웹 검색으로 확인한 코드표·악보 메타데이터에서 옮겼습니다. '
        f'악보 준비 완료 {ready}곡, 부분 확인 {partial}곡, 검수 대기 {pending}곡. '
        '마디 배치는 코드표 순서를 4박 카드로 정리한 연습용이며, 원곡 세부 마디와 다를 수 있습니다. '
        '원터치 버튼에 없는 코드는 SimplifyChord 슬롯(최대 5개)으로 안내합니다.')
    meta['sourceDisclosure'] = (
        '원본 152곡 전체 데이터는 여전히 미확보입니다. 2026-11-22 확인한 재생목록 공개 168개 영상과 접근 불가 42개 사유를 기록했고, '
        '그중 실제 곡명이 확인된 곡은 남자키·박자·BPM·원터치 악보를 채웠습니다. 확인하지 못한 곡은 검수 대기로 남깁니다.')

    (BASE / 'data' / 'songs.seed.json').write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (BASE / 'data' / 'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (BASE / 'src' / 'seed.js').write_text(
        'window.STRUM_SEED = ' + json.dumps({'songs': songs, 'sources': sources, 'meta': meta},
                                            ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')
    cols = ['id', 'title', 'artist', 'sourceIndices', 'verification', 'videoUrl', 'videoStatus', 'audioUrl',
            'key', 'maleKey', 'bpm', 'timeSignature', 'chords', 'chordStatus', 'strumming', 'level', 'tags',
            'notes', 'setlist']
    for name_, only_verified in (('songs.all.csv', False), ('songs.verified.csv', True)):
        with (BASE / 'data' / name_).open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
            w.writeheader()
            for s in songs:
                if only_verified and not s['id'].startswith('verified-'):
                    continue
                row = {c: s.get(c, '') for c in cols}
                row['sourceIndices'] = '|'.join(map(str, s['sourceIndices']))
                row['tags'] = '|'.join(s.get('tags') or [])
                row['setlist'] = str(s['setlist']).lower()
                row['timeSignature'] = (s.get('chart') or {}).get('timeSignature', '')
                w.writerow(row)
    with (BASE / 'data' / 'chart-coverage.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'title', 'artist', '원키', '남자키', 'Capo', '폼/설정', '박자', 'BPM',
                    '원터치 매핑', '코드 수', '슬롯', '단계', '상태'])
        w.writerows(coverage_rows)
    print(f'ready={ready} partial={partial} pending={pending}')


if __name__ == '__main__':
    main()
