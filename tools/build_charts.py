#!/usr/bin/env python3
"""곡 데이터에 남자키·카포·원터치 컬러 악보·SimplifyChord 슬롯을 계산해 병합한다.

실행: python3 tools/build_charts.py
입력: data/songs.seed.json (+ tools/chart_data.py)
출력: data/songs.seed.json, data/songs.all.csv, data/songs.verified.csv, src/seed.js, data/chart-coverage.csv
"""
import csv
import json
import re
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'tools'))
from chart_data import CHARTS, FEMALE_ORIGINAL  # noqa: E402
from playlist_data import WORK_META, PLAYLIST, OVERRIDES  # noqa: E402
from collections import Counter  # noqa: E402

SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT_OF = {'D#': 'Eb', 'G#': 'Ab', 'A#': 'Bb'}
PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6,
      'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11,
      'Cb': 11, 'Fb': 4}
SHAPES = {'C': (0, 'maj'), 'D': (2, 'maj'), 'E': (4, 'maj'), 'F': (5, 'maj'), 'G': (7, 'maj'),
          'Cm': (0, 'min'), 'Dm': (2, 'min'), 'Em': (4, 'min'), 'Fm': (5, 'min'), 'Gm': (7, 'min')}
ONE_TOUCH_ORDER = ['C', 'Dm', 'Em', 'F', 'G', 'Cm', 'D', 'E', 'Fm', 'Gm']
MAX_SLOTS = 8  # SimplifyChord는 프렛마다 1개(공식 안내 최대 12개) → 화면에는 8개까지 안내
# 원터치 버튼에 없는 코드를 슬롯에 넣을 때 흔히 쓰는 약식 대안(사실 기반 제안, 연주자 선택)
EASY_ALT = {
    'B': 'B7(x21202) 약식', 'Bm': 'Bm7(x20202)', 'Bb': 'Bb(6프렛 바레) 또는 A# 약식',
    'Bbm': 'Bbm7(x13121)', 'Am': 'Am7(x02010)', 'A': 'A(x02220)', 'F': 'Fmaj7(xx3210) 약식',
    'Fm': 'Fm7(131111) 3현만', 'C#m': 'C#m7(x46454)', 'G#': 'G#7(464544)', 'G#m': 'G#m7(464444)',
    'D#': 'D#(x68886)', 'A#m': 'A#m7(x13121)', 'Dm': 'Dm7(xx0211)', 'Cm': 'Cm7(x35343)',
    'Eb': 'Eb(x68886)', 'Ab': 'Ab(466544)', 'Db': 'Db(x46664)', 'E7': 'E7(020100)',
    'A7': 'A7(x02020)', 'G7': 'G7(320001)', 'D7': 'D7(xx0212)', 'B7': 'B7(x21202)',
    'F#': 'F#(244322)', 'F#m': 'F#m(244222)', 'Bm7': 'Bm7(x20202)', 'Am7': 'Am7(x02010)',
    'Gb': 'Gb(244322) 2프렛 바레', 'Gbm': 'Gbm(244222) 2프렛 바레', 'Faug': 'F7(xx3241) 근사 또는 Fmaj7',
    'F7': 'F7(131211)', 'Ab7': 'Ab7(464544)', 'Eb7': 'Eb7(x6564x)', 'C#7': 'C#7(x43404)',
    'C#m7': 'C#m7(x46454)', 'F#m7': 'F#m7(242222)', 'Cm7': 'Cm7(x35343)', 'Fm7': 'Fm7(131111)',
    'Bb7': 'Bb7(x13131)', 'Ebmaj7': 'Ebmaj7(xx1333)', 'Abmaj7': 'Abmaj7(465544)', 'Bbm7': 'Bbm7(x13121)',
    'E': 'E(022100)', 'B': 'B7(x21202) 약식', 'C#': 'Db(x46664) 4프렛 바레',
    'Ebm': 'Ebm7(x68676) 6프렛 바레', 'Abm7': 'Abm7(464444)', 'Dbm': 'Dbm(x46664) 4프렛 바레',
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
    if prefer_flat and s == 'F#':
        return 'Gb'
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


AUTO = json.loads((BASE / 'tools' / 'auto_charts.json').read_text(encoding='utf-8')) \
    if (BASE / 'tools' / 'auto_charts.json').exists() else {}
SONG_WORKS = {
    'verified-009': 'yeppeo', 'restored-140': 'yeppeo', 'verified-011': 'chunghon',
    'verified-019': 'saenggak', 'verified-014': 'sabyeol', 'restored-122': 'vancouver',
    'restored-100': 'goodbyebye', 'restored-093': 'muje', 'restored-128': 'eoddeoke',
    'restored-150': 'whatislove', 'restored-201': 'her', 'verified-021': 'narssi',
    'verified-017': 'jangkam', 'verified-024': 'datunsaram', 'verified-023': 'saranghan-maeum',
    'verified-004': 'ten-thousand-hours', 'verified-005': 'chueok',
}
FEMALE_SLUGS = {slug for slug, v in WORK_META.items() if v[2] == 'f'}
WORK_IDS = {}  # build 단계에서 채운다


def ideal_shift(sid):
    """남자키 목표: 남성 원곡은 원키 그대로(0반음), 여성 원곡만 -5반음."""
    if sid in FEMALE_ORIGINAL or WORK_IDS.get(sid) in FEMALE_SLUGS:
        return 5
    return 0


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
    # 남성 원곡은 원키 고정(이조 0반음), 여성 원곡은 -5반음 고정. 카포만으로 원터치 버튼에 맞춘다.
    shifts = [5] if ideal == 5 else [0]
    for shift in shifts:
        male = {c: shift_name(p['root'], shift, prefer_flat) + p['suffix']
                + (('/' + shift_name(p['bass'], shift, prefer_flat)) if p['bass'] else '')
                for c, p in parsed}
        male_pc = {c: PC[shift_name(p['root'], shift, prefer_flat)] for c, p in parsed}
        capo_range = [int(data['capo'])] if data.get('capo') is not None else range(0, 8)
        for capo in capo_range:
            mapped = sum(1 for c, p in parsed if find_button(male_pc[c], p['quality'], capo))
            unmapped = len(parsed) - mapped
            mapped_occ = sum(weight[c] for c, p in parsed if find_button(male_pc[c], p['quality'], capo))
            tonic = parse_chord(orig)
            tonic_ok = find_button((PC[tonic['root']] - shift) % 12, tonic['quality'], capo) is not None
            # ① 슬롯(원터치에 없는 코드) 수를 가장 작게 ② 카포는 낮게 ③ 으뜸화음을 버튼으로 잡을 수 있게
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
    if data.get('transpose'):
        semis = int(data['transpose'])
        org = shift_name(parse_chord(org)['root'], -semis, False) + (
            'm' if parse_chord(org)['quality'] == 'min' else '')
        data = dict(data)
        data['originalKey'] = org
        data['sections'] = [
            {'name': sec['name'],
             'bars': [[shift_name(parse_chord(c)['root'], -semis, 'b' in org) + parse_chord(c)['suffix']
                       + (('/' + shift_name(parse_chord(c)['bass'], -semis, 'b' in org))
                          if parse_chord(c)['bass'] else '')
                       for c in bar] for bar in sec['bars']]}
            for sec in data['sections']
        ]
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
                # 증5화음(aug)·감5화음(dim)은 3화음 버튼으로 대신할 수 없어 슬롯으로 넘긴다
                if any(k in pc_['suffix'] for k in ('aug', 'dim', 'b5', '°', '-5')):
                    btn = None
                if btn is None:
                    if c not in slot_map:
                        if len(slot_list) >= MAX_SLOTS:
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
        'basis': data.get('basis') or '코드표 순서를 4박 마디 카드로 정리한 연습용 배치입니다. 원곡의 세부 마디 배치와 다를 수 있습니다.',
        'evidence': [{'label': a, 'url': b, 'note': c} for a, b, c in data.get('evidence', [])],
    }
    return chart, male_key


def work_chart_data(slug):
    """곡 slug → build_chart 입력(dict). 직접 정리한 OVERRIDES 가 자동 초안보다 우선."""
    if slug in OVERRIDES:
        return dict(OVERRIDES[slug])
    wm = WORK_META.get(slug)
    if wm and wm[3] == 'pending':
        return None
    auto = AUTO.get(slug)
    if not auto:
        return None
    meta = WORK_META.get(slug)
    title = (meta[0] if meta else auto.get('title')) or slug
    sections = [{'name': s['name'], 'bars': s['bars']} for s in auto['sections'] if s['bars']]
    if not sections:
        return None
    return {
        'originalKey': auto['originalKey'],
        'timeSignature': auto.get('timeSignature') or '4/4',
        'bpm': auto.get('bpm'),
        'sections': sections,
        'stroke': '↓ · ↓↑ · ↓↑ (8분 중심, 코드는 마디 앞에서)',
        'why': f'코드스코어 공개 미리보기 {sum(len(s["bars"]) for s in sections)}마디의 코드 진행을 4박 카드로 옮겼다. 원터치에 없는 코드는 SimplifyChord 슬롯으로 넘긴다.',
        'evidence': [
            ('코드스코어 코드 악보(원키·박자·BPM·마디 코드)', f'https://chordscore.com/notes/{auto["scoreId"]}',
             f'원키 {auto["originalKey"]} · {auto.get("timeSignature")} · {auto.get("bpm")}bpm · {title}'),
        ],
    }


def main():
    songs = json.loads((BASE / 'data' / 'songs.seed.json').read_text(encoding='utf-8'))
    sources = json.loads((BASE / 'data' / 'source-videos.seed.json').read_text(encoding='utf-8'))
    meta = json.loads((BASE / 'data' / 'metadata.json').read_text(encoding='utf-8'))
    by_id = {s['id']: s for s in songs}
    for s in songs:
        item = PLAYLIST.get(s['id'])
        if item and item[1]:
            WORK_IDS[s['id']] = item[1]
        elif s['id'] in SONG_WORKS:
            WORK_IDS[s['id']] = SONG_WORKS[s['id']]
    coverage_rows = []
    ready = partial = pending = 0
    references = originals = 0
    copies = []
    for s in songs:
        pitem = PLAYLIST.get(s['id'])
        if pitem:
            kind, target, note = pitem
            s['playlistKind'] = kind
            s['categoryNote'] = note
            if target and target in WORK_META:
                wt, wa = WORK_META[target][0], WORK_META[target][1]
                s['workTitle'] = wt
                s['workArtist'] = wa
            if kind == 'reference':
                s['category'] = 'reference'
                s['chartStatus'] = 'reference'
                s.pop('chart', None)
                s['chartNote'] = '비음악·참고 영상으로 분리했습니다.'
                references += 1
                continue
            if kind == 'original':
                s['category'] = 'original'
                s['chartStatus'] = 'original'
                s.pop('chart', None)
                s['chartNote'] = '인터넷에 악보가 없는 자작곡입니다. 음원을 올리면 채보할 수 있습니다.'
                originals += 1
                continue
            if kind == 'copy':
                copies.append((s, target))
                continue
            data = work_chart_data(target) if target else None
            if data and data.get('missing'):
                data = None
            if not data:
                data = CHARTS.get(s['id'])
        else:
            if s['id'] in SONG_WORKS and '미확인' in s.get('artist', ''):
                wt, wa = WORK_META[SONG_WORKS[s['id']]][0], WORK_META[SONG_WORKS[s['id']]][1]
                s['workTitle'] = wt
                s['workArtist'] = wa
            data = CHARTS.get(s['id'])
            if s['id'] in SONG_WORKS:
                wdata = work_chart_data(SONG_WORKS[s['id']])
                if wdata and wdata.get('sections'):
                    data = wdata
                elif not data:
                    data = wdata
        if not data:
            if s.get('chart'):
                del s['chart']
            s['chartStatus'] = 'pending'
            s['chartNote'] = '코드·키·박자 확인 전 — 검수 대기'
            s['category'] = 'pending'
            if re.match(r'^(verified|restored)-', s['id']) or s['verification'] in ('added-by-user', 'imported'):
                pending += 1
            elif pitem:
                pending += 1
            continue
        if data.get('missing'):
            s['chartStatus'] = 'pending'
            s['chartNote'] = data['missing']
            s['category'] = 'pending'
            s.pop('chart', None)
            pending += 1
            continue
        if data.get('pending') and not data.get('sections'):
            # 확인된 키·BPM·근거 링크만 있는 곡: 악보 없이 '검수 대기'를 유지하되,
            # 확인한 값과 근거 링크는 곡 정보/근거 화면에서 바로 열 수 있게 남긴다.
            orig = data.get('originalKey', '')
            ts = data.get('timeSignature', '') or '미확인'
            bpm = data.get('bpm') or 0
            male_key = ''
            shift = 0
            if orig and orig != '미확인':
                try:
                    b_ = parse_chord(orig)
                    pref_ = 'b' in orig
                    shift = ideal_shift(s['id'])
                    male_key = name((PC[b_['root']] - shift) % 12, pref_)
                    if b_['quality'] == 'min':
                        male_key += 'm'
                except (KeyError, ValueError):
                    male_key, shift = '', 0
            s['chart'] = {
                'status': 'pending',
                'timeSignature': ts,
                'timeNote': data.get('timeNote', ''),
                'bpm': bpm,
                'bpmNote': data.get('bpmNote', ''),
                'originalKey': orig,
                'maleKey': male_key,
                'maleShift': shift,
                'capo': None,
                'formButton': '', 'formKey': '', 'formText': '',
                'sections': [], 'slots': [], 'stage': 3,
                'stroke': '', 'percussive': '', 'why': '',
                'coverage': {'mapped': 0, 'total': 0, 'unmapped': 0},
                'basis': '',
                'note': data['pending'],
                'evidence': [{'label': a, 'url': b, 'note': c} for a, b, c in data.get('evidence', [])],
            }
            s['chartStatus'] = 'pending'
            s['category'] = 'pending'
            s['chartNote'] = data['pending']
            s['key'] = orig
            if male_key:
                s['maleKey'] = male_key
            s['bpm'] = bpm or None
            s['timeSignature'] = ts
            s['chordStatus'] = '미확인'
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
                'basis': '', 'note': data.get('partial', ''),
                'evidence': [{'label': a, 'url': b, 'note': c} for a, b, c in data.get('evidence', [])],
            }
            if chart['originalKey']:
                try:
                    b_ = parse_chord(chart['originalKey'])
                    pref_ = 'b' in chart['originalKey']
                    mk_ = name((PC[b_['root']] - ideal_shift(s['id'])) % 12, pref_)
                    if b_['quality'] == 'min':
                        mk_ += 'm'
                    chart['maleKey'] = mk_
                    chart['maleShift'] = ideal_shift(s['id'])
                    s['maleKey'] = mk_
                except (KeyError, ValueError):
                    pass
            s['chart'] = chart
            s['chartStatus'] = 'partial'
            s['chartNote'] = data.get('partial', '')
            s['category'] = 'partial'
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
            s['category'] = 'partial'
            partial += 1
        else:
            s['chartStatus'] = 'ready'
            s['category'] = 'chart'
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
        if pitem and pitem[0] == 'music' and s.get('workTitle'):
            s['tags'].append('커버 영상')
        if chart['status'] == 'ready' and s['chartStage'] == 1 and '오른손 1단계' not in s['tags']:
            s['tags'].append('오른손 1단계')
        coverage_rows.append([s['id'], s['title'], s['artist'], chart['originalKey'], male_key,
                              chart['capo'], chart['formText'], chart['timeSignature'], chart['bpm'],
                              chart['coverage']['mapped'], chart['coverage']['total'],
                              len(chart['slots']), chart['stage'], chart['status']])
    # 커버 영상 항목: 이미 만든 곡의 악보를 그대로 붙인다(중복 생성 없음)
    for s, src_id in copies:
        src = by_id.get(src_id)
        s['workTitle'] = (src or {}).get('title', '') or s.get('workTitle', '')
        s['workArtist'] = (src or {}).get('artist', '') or s.get('workArtist', '')
        if src and src.get('chart'):
            s['chart'] = json.loads(json.dumps(src['chart']))
            s['chartStatus'] = src.get('chartStatus', 'ready')
            s['category'] = src.get('category', 'chart')
            s['key'] = src.get('key', '')
            s['maleKey'] = src.get('maleKey', '')
            s['bpm'] = src.get('bpm')
            s['timeSignature'] = src.get('timeSignature', '')
            s['chords'] = src.get('chords', '')
            s['chordStatus'] = src.get('chordStatus', '')
            s['strumming'] = src.get('strumming', '')
            s['chartStage'] = src.get('chartStage')
            s['chartNote'] = '같은 곡의 악보를 그대로 연결했습니다.'
            s['tags'] = list(dict.fromkeys((s.get('tags') or []) + (src.get('tags') or [])))
            if s['chartStatus'] == 'ready':
                ready += 1
            else:
                partial += 1
            coverage_rows.append([s['id'], s['workTitle'], s['workArtist'], s['key'], s['maleKey'],
                                  (s.get('chart') or {}).get('capo'), (s.get('chart') or {}).get('formText', ''),
                                  s.get('timeSignature', ''), s.get('bpm'),
                                  (s.get('chart') or {}).get('coverage', {}).get('mapped', 0),
                                  (s.get('chart') or {}).get('coverage', {}).get('total', 0),
                                  len((s.get('chart') or {}).get('slots') or []),
                                  s.get('chartStage'), s['chartStatus']])
        else:
            s['chartStatus'] = 'pending'
            s['category'] = 'pending'
            s.pop('chart', None)
            s['chartNote'] = '연결할 악보를 찾지 못했습니다.'
            pending += 1

    chart_titles = {}
    for s in songs:
        if s.get('category') in ('chart', 'partial'):
            k = (s.get('workTitle') or s['title'])
            chart_titles.setdefault(k, s.get('workArtist') or s['artist'])
    ready = sum(1 for s in songs if s.get('category') == 'chart')
    partial = sum(1 for s in songs if s.get('category') == 'partial')
    pending = sum(1 for s in songs if s.get('category') == 'pending')
    references = sum(1 for s in songs if s.get('category') == 'reference')
    originals = sum(1 for s in songs if s.get('category') == 'original')
    meta['seedVersion'] = 9
    meta['chartVersion'] = '2026-11-22'
    meta['chartReadyCount'] = ready
    meta['chartPartialCount'] = partial
    meta['chartPendingCount'] = pending
    meta['nonMusicCount'] = references
    meta['originalWorkCount'] = originals
    meta['uniqueChartSongCount'] = len(chart_titles)
    meta['categoryCounts'] = {
        'chart': ready, 'partial': partial, 'pending': pending,
        'reference': references, 'original': originals,
    }
    meta['originalWorks'] = [
        {'id': s['id'], 'title': s.get('workTitle') or s['title'], 'artist': s.get('workArtist') or s['artist'],
         'note': s.get('categoryNote', '')}
        for s in songs if s.get('category') == 'pending'
    ]
    meta['chartDisclosure'] = (
        '남자키는 남성 원곡이면 원키 그대로(이조 0반음), 여성 원곡이면 -5반음으로 잡고 그 목표 키를 AeroBand 원터치 버튼에 맞추도록 카포를 골랐습니다. '
        f'남자키·박자·BPM·코드 진행은 2026-11-22 웹 검색으로 확인한 코드표·악보 메타데이터와, 주성 님이 직접 올린 음원 3곳(#108 · #172 · #202 이기찬 ‘닮은 사람’ MR)의 오디오 분석에서 옮겼습니다. '
        f'악보 준비 완료 {ready}곡(서로 다른 곡 {len(chart_titles)}곡), 부분 확인 {partial}곡, 검수 대기 {pending}곡, '
        f'비음악·참고 영상 {references}개, 자작곡 {originals}개. '
        '마디 배치는 코드표 순서를 4박 카드로 정리한 연습용이며, 원곡 세부 마디와 다를 수 있습니다. '
        '음원 분석 곡(#108 · #172 · #202)과 자동분석 후보 곡은 청음 검수를 권장합니다. '
        '키·코드가 확인되지 않은 곡은 추측값을 넣지 않고 검수 대기로 두되, 확인된 BPM·키와 근거 링크만 곡 정보 화면에 남겼습니다. '
        '원터치 버튼에 없는 코드는 SimplifyChord 슬롯(최대 8개)으로 안내합니다.')
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
