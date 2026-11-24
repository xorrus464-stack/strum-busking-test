#!/usr/bin/env python3
"""14버튼 밖 코드를 '최대한 편한 손 모양'으로 남기는 카포 재최적화 (2026-11-25).

배경: 주성 님 지시 — "카포 써도 없는 코드 있는 노래 있으면 최대한 편한 코드만 남게 카포를 쓴
악보로 만들고, 카포 써도 없는 코드는 진짜 코드로 악보에 손가락 운지법까지 다 나오게."

하는 일
1. 곡마다 카포 0~11을 모두 계산해 ① 14버튼 밖 코드(슬롯) 종류 수 ② 슬롯이 나오는 마디 수
   ③ 남는 코드의 손 모양 난이도(오픈 0 < 부분 바레 2 < 전체 바레 3~4) ④ 카포 높이 순으로 최선을 고른다.
   - 카포만 바꾸므로 maleKey·울리는 코드(sound)는 그대로다.
   - 지금 슬롯 0개인 곡(14버튼 완주)은 ①②③이 모두 0으로 같으므로 카포를 건드리지 않는다.
2. 남는 슬롯마다 진짜 코드 이름 + 기타 운지(6→1번줄 프렛, 손가락, 바레, 카포 기준 위치)를 넣는다.
3. seed.js / songs.seed.json / metadata.json / songs.all.csv / songs.verified.csv / chart-coverage.csv 갱신.

실행: python3 tools/capo_optimize_2026_11_25.py [--write]
"""
import csv
import json
import pathlib
import sys
from collections import Counter

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'tools'))
from chord_shapes import describe, parse as parse_chord_name, shape_name, FAMILY_LABEL  # noqa: E402

SEED_JS = BASE / 'src' / 'seed.js'
SEED_JSON = BASE / 'data' / 'songs.seed.json'

PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6,
      'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT_OF = {'D#': 'Eb', 'G#': 'Ab', 'A#': 'Bb', 'C#': 'Db', 'F#': 'Gb'}
BTNS14 = ['C', 'Dm', 'Em', 'F', 'G', 'Am', 'Bdim', 'Cm', 'D', 'E', 'Fm', 'Gm', 'A', 'Bm']
BTN_SHAPE = {'C': (0, 'maj'), 'Dm': (2, 'min'), 'Em': (4, 'min'), 'F': (5, 'maj'), 'G': (7, 'maj'),
             'Am': (9, 'min'), 'Bdim': (11, 'dim'), 'Cm': (0, 'min'), 'D': (2, 'maj'),
             'E': (4, 'maj'), 'Fm': (5, 'min'), 'Gm': (7, 'min'), 'A': (9, 'maj'), 'Bm': (11, 'min')}
MAX_SLOTS = 8
CAPO_MAX = 11


def split_chord(chord):
    t = str(chord).split('/')[0].strip().replace('♭', 'b').replace('♯', '#')
    i = 1
    while i < len(t) and t[i] in '#b':
        i += 1
    return t[:i], t[i:]


def quality_of(sound):
    """버튼으로 잡을 수 있는 3화음 성질. aug는 버튼이 없어 None."""
    _root, suf = split_chord(sound)
    low = suf.lower()
    if 'aug' in low or '+' in low:
        return None
    if 'dim' in low or '°' in suf or 'b5' in low or '-5' in low or 'ø' in suf:
        return 'dim'
    if low.startswith('m') and not low.startswith('maj'):
        return 'min'
    return 'maj'


def find_button(sound, capo):
    root, _suf = split_chord(sound)
    q = quality_of(sound)
    if q is None or root not in PC:
        return None
    pc = PC[root]
    for btn in BTNS14:
        bp, bq = BTN_SHAPE[btn]
        if bq == q and (bp + capo) % 12 == pc:
            return btn
    return None


def name_of(pc, prefer_flat=False):
    s = SHARP[pc % 12]
    if s in ('D#', 'G#', 'A#'):
        return FLAT_OF[s]
    if prefer_flat and s in ('C#', 'F#'):
        return FLAT_OF[s]
    return s


def evaluate(chords, capo):
    """카포 후보의 지표.

    uniq  : 14버튼 밖 코드 종류 수(SimplifyChord에 넣을 코드 수)
    effort: 손으로 잡아야 하는 마디의 난이도 합(Σ 난이도×마디 수) — 낮을수록 편함
    occ   : 슬롯이 나오는 마디 수
    clash : 남는 코드 이름이 14버튼 이름과 겹치는 수(버튼으로 착각하기 쉬움)
    """
    uniq = list(dict.fromkeys(chords))
    unmapped = [c for c in uniq if find_button(c, capo) is None]
    occ = sum(1 for c in chords if find_button(c, capo) is None)
    diffs = {c: describe(c, capo)['difficulty'] for c in unmapped}
    effort = sum(diffs[c] * chords.count(c) for c in unmapped)
    clash = sum(1 for c in unmapped if split_chord(c)[0] in BTN_SHAPE)
    return {'uniq': len(unmapped), 'occ': occ, 'diff': sum(diffs.values()), 'effort': effort,
            'clash': clash, 'maxdiff': max(diffs.values()) if diffs else 0, 'unmapped': unmapped}


def choose_capo(chords, old_capo):
    cands = []
    for capo in range(0, CAPO_MAX + 1):
        e = evaluate(chords, capo)
        e['capo'] = capo
        cands.append(e)
    def key(e):
        return (e['uniq'], e['effort'], e['occ'], e['clash'])
    cands.sort(key=lambda e: key(e) + (e['capo'] != old_capo, e['capo']))
    best = cands[0]
    old = next((e for e in cands if e['capo'] == old_capo), None)
    # 지금 카포가 같거나 더 좋으면 그대로 둔다(이미 맞춰 둔 폼을 함부로 바꾸지 않는다).
    if old and key(old) <= key(best):
        return old, cands
    return best, cands


def tip_for(info):
    """손 모양 팁 — 바레·약식·슬래시 코드 안내(검증된 운지에만 붙인다)."""
    tips = []
    b = info.get('barre')
    if b:
        span = b['from'] - b['to'] + 1
        if span >= 5:
            tips.append(f"1번 손가락을 {b['from']}~{b['to']}번줄 {b['fret']}프렛에 눕혀 바레로 잡아요. "
                        '손가락 끝이 1번줄 밖으로 조금 나오게 두면 1번줄이 잘 울립니다.')
        else:
            tips.append(f"1번 손가락으로 {b['from']}~{b['to']}번줄 {b['fret']}프렛을 함께 눌러요(미니 바레).")
    if info.get('difficulty', 0) >= 4:
        tips.append('프렛이 높은 자리라 줄 장력이 낮아 힘이 덜 들어요. 4·3·2번줄부터 소리를 확인해요.')
    if info.get('approximate'):
        tips.append('3화음(버튼 코드)으로 근사한 모양이에요. 원래 텐션 음은 생략됩니다.')
    if info.get('bassNote'):
        tips.append(info['bassNote'])
    if info.get('capo'):
        tips.append(f"카포 +{info['capo']}를 0프렛으로 보고 잡는 모양이에요.")
    return ' '.join(tips)


def slot_object(chord, slot_no, orig, capo):
    info = describe(chord, capo)
    return {
        'slot': slot_no,
        'chord': chord,
        'orig': orig if orig else chord,
        'shape': info['shape'],
        'capo': capo,
        'frets': info['frets'],
        'fingers': info['fingers'],
        'barre': info['barre'],
        'base': info['base'],
        'fingering': info['fingering'],
        'difficulty': info['difficulty'],
        'approximate': bool(info.get('approximate')),
        'bassNote': info.get('bassNote', ''),
        'tip': tip_for(info),
        'why': ((f"카포 +{capo}에서는 " if capo else '카포 없이(0프렛)에서는 ')
                + f"{chord} 코드가 {info['shape']} 모양이 되어 14버튼(3화음)에 없습니다. "
                  '손으로 잡는 운지를 그대로 적었습니다.'),
    }


def stage_formula(total_unique, slots):
    return 1 if total_unique <= 4 else (2 if total_unique <= 6 and slots <= 1 else 3)


def optimize(chart):
    cells = [cell for sec in chart['sections'] for bar in sec['bars'] for cell in bar]
    chords = [c['sound'] for c in cells]
    uniq = list(dict.fromkeys(chords))
    old_capo = int(chart.get('capo') or 0)
    old_slots = len(chart.get('slots') or [])
    best, cands = choose_capo(chords, old_capo)
    capo = best['capo']
    unmapped = [c for c in uniq if find_button(c, capo) is None]
    # 슬롯 번호는 많이 나오는 코드부터(연습 우선순위)
    count = Counter(chords)
    unmapped.sort(key=lambda c: (-count[c], c))
    slot_index = {c: i + 1 for i, c in enumerate(unmapped[:MAX_SLOTS])}
    overflow = set(unmapped[MAX_SLOTS:])

    orig_of = {}
    for cell in cells:
        orig_of.setdefault(cell['sound'], cell.get('orig') or cell['sound'])

    for cell in cells:
        sound = cell['sound']
        btn = find_button(sound, capo)
        if sound in overflow:
            btn = None
        cell['btn'] = btn
        cell['slot'] = 0 if btn else slot_index.get(sound, 0)
        cell['quality'] = quality_of(sound) or cell.get('quality') or 'maj'

    slots = [slot_object(c, slot_index[c], orig_of.get(c), capo) for c in unmapped[:MAX_SLOTS]]

    male_key = chart.get('maleKey') or ''
    prefer_flat = 'b' in male_key or male_key in ('F',)
    tonic_btn = find_button(male_key, capo) if male_key else None
    chart['capo'] = capo
    chart['slots'] = slots
    chart['formButton'] = tonic_btn or ''
    chart['formKey'] = name_of(capo % 12, prefer_flat)
    chart['formText'] = (f'{tonic_btn}폼 · Capo +{capo}' if tonic_btn else f'Capo +{capo}')
    chart['coverage'] = {'mapped': len(uniq) - len(unmapped), 'total': len(uniq), 'unmapped': len(unmapped)}
    chart['shapeInfo'] = {
        'capo': capo,
        'chords': [{'chord': c, 'shape': describe(c, capo)['shape'],
                    'fingering': describe(c, capo)['fingering'],
                    'difficulty': describe(c, capo)['difficulty']} for c in unmapped[:MAX_SLOTS]],
        'note': ('남는 코드는 카포를 뺀 손 모양 기준으로 쉬운 순서(오픈 → 미니 바레 → 바레)로 골랐습니다.'
                 if unmapped else '14버튼만으로 완주 — 손으로 잡을 코드가 없습니다.'),
    }
    cur_stage = chart.get('stage') if chart.get('stage') in (1, 2, 3, 4) else None
    if chart.get('percussiveReady') or cur_stage == 4:
        new_stage = cur_stage or 3
    elif len(slots) < old_slots:
        f = stage_formula(len(uniq), len(slots))
        new_stage = min(cur_stage, f) if cur_stage else f
    else:
        new_stage = cur_stage
    chart['stage'] = new_stage
    chart['remap'] = {
        'btnSet': 14, 'date': '2026-11-25', 'mode': 'easy-leftover',
        'capoFrom': old_capo, 'capoTo': capo,
        'slotsFrom': old_slots, 'slotsTo': len(slots),
    }
    return {'id': chart.get('id'), 'capo': capo, 'oldCapo': old_capo,
            'slots': len(slots), 'oldSlots': old_slots, 'stage': new_stage,
            'oldStage': cur_stage, 'uniq': len(uniq), 'unmapped': unmapped,
            'diff': best['diff'], 'occ': best['occ'], 'effort': best['effort']}


def load_seed():
    txt = SEED_JS.read_text(encoding='utf-8')
    head = 'window.STRUM_SEED = '
    i = txt.index(head) + len(head)
    body = txt[i:].rstrip()
    assert body.endswith(';')
    return json.loads(body[:-1].rstrip())


def write_coverage_csv(songs):
    """data/chart-coverage.csv — 기존 열 구성을 유지하고 남는 코드·운지 열을 덧붙인다."""
    cols = ['id', 'title', 'artist', '원키', '남자키', 'Capo', '폼/설정', '박자', 'BPM',
            '원터치 매핑', '코드 수', '슬롯', '단계', '상태', '남는 코드', '손 모양 운지']
    rows = []
    for s in songs:
        c = s.get('chart') or {}
        if not c.get('sections'):
            continue
        rows.append({
            'id': s['id'], 'title': s['title'], 'artist': s['artist'],
            '원키': c.get('originalKey'), '남자키': c.get('maleKey'), 'Capo': c.get('capo'),
            '폼/설정': c.get('formText'), '박자': c.get('timeSignature'), 'BPM': c.get('bpm'),
            '원터치 매핑': (c.get('coverage') or {}).get('mapped'),
            '코드 수': (c.get('coverage') or {}).get('total'),
            '슬롯': len(c.get('slots') or []), '단계': c.get('stage'),
            '상태': s.get('chartStatus'),
            '남는 코드': '|'.join(x['chord'] for x in (c.get('slots') or [])),
            '손 모양 운지': ' ;; '.join(f"{x['chord']}={x['shape']}({x['fingering'].split(' · ')[0]})"
                                     for x in (c.get('slots') or [])),
        })
    with (BASE / 'data' / 'chart-coverage.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\r\n')
        w.writeheader()
        w.writerows(rows)


def main():
    write = '--write' in sys.argv
    seed = load_seed()
    songs = seed['songs']
    infos = []
    for s in songs:
        c = s.get('chart')
        if not isinstance(c, dict) or not c.get('sections'):
            continue
        info = optimize(c)
        info['title'] = s['title']
        info['id'] = s['id']
        infos.append(info)

    # 다시 돌려도 '이전 기준' 통계는 처음 값(14버튼 v22 = 62슬롯 / 124곡 완주)을 유지한다.
    prev_meta = seed['meta'].get('capoOptimize') or {}
    prev_zero = prev_meta.get('prevZeroSlotCharts', sum(1 for i in infos if i['oldSlots'] == 0))
    prev_slot_total = prev_meta.get('prevSlotTotal', sum(i['oldSlots'] for i in infos))
    zero = [i for i in infos if i['slots'] == 0]
    print(f"악보 {len(infos)}개 · 슬롯 0개 {prev_zero} → {len(zero)}")
    print(f"슬롯 합계 {prev_slot_total} → {sum(i['slots'] for i in infos)}")
    print(f"카포 변경 {sum(1 for i in infos if i['capo'] != i['oldCapo'])}곡 · 단계 변경 {sum(1 for i in infos if i['stage'] != i['oldStage'])}곡")
    print('남은 슬롯 분포', Counter(i['slots'] for i in infos).most_common())
    print('\n[카포 변경]')
    for i in infos:
        if i['capo'] != i['oldCapo']:
            print(f"  {i['oldCapo']}→{i['capo']}  슬롯 {i['oldSlots']}→{i['slots']}  난이도{i['diff']}  {i['id']} {i['title'][:34]}")
    print('\n[단계 변경]')
    for i in infos:
        if i['stage'] != i['oldStage']:
            print(f"  {i['oldStage']}→{i['stage']}  슬롯 {i['oldSlots']}→{i['slots']}  {i['id']} {i['title'][:34]}")
    print('\n[남은 코드]')
    for i in sorted([x for x in infos if x['slots']], key=lambda x: (-x['slots'], x['id'])):
        print(f"  카포{i['capo']:2d} 슬롯{i['slots']} 난이도{i['diff']:2d}  {i['id']}  {', '.join(i['unmapped'])}")

    if write:
        meta = seed['meta']
        meta['seedVersion'] = 23
        meta['capoOptimize'] = {
            'date': '2026-11-25',
            'chartCount': len(infos),
            'prevZeroSlotCharts': prev_zero,
            'zeroSlotCharts': len(zero),
            'prevSlotTotal': prev_slot_total,
            'slotTotal': sum(i['slots'] for i in infos),
            'capoChangedCount': sum(1 for i in infos if i['capo'] != i['oldCapo']),
            'stageChangedCount': sum(1 for i in infos if i['stage'] != i['oldStage']),
            'capoRange': [0, CAPO_MAX],
        }
        meta['btn14']['zeroSlotCount'] = len(zero)
        meta['btn14']['slotChartCount'] = len(infos) - len(zero)
        meta['btn14']['slotTotal'] = sum(i['slots'] for i in infos)
        old_disc = meta.get('chartDisclosure', '')
        add = ('2026-11-25 추가: 14버튼에도 없는 코드가 남는 곡은 카포를 다시 계산해 ① 남는 코드 종류 '
               '② 나오는 마디 수 ③ 손 모양 난이도(오픈 < 미니 바레 < 바레) 순으로 가장 편한 카포를 골랐습니다. '
               '남는 코드는 S1·S2 대신 진짜 코드 이름과 기타 운지(6→1번줄 프렛·손가락·바레, 카포 기준)를 표시하고, '
               '모든 운지는 실제 음정으로 검증했습니다(근음·3음 포함, 코드 밖 음 없음).')
        meta['chartDisclosure'] = (old_disc + ' ' + add).strip()
        out = 'window.STRUM_SEED = ' + json.dumps(seed, ensure_ascii=False, separators=(',', ':')) + ';\n'
        SEED_JS.write_text(out, encoding='utf-8')
        SEED_JSON.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (BASE / 'data' / 'metadata.json').write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        write_coverage_csv(songs)
    print('\nwritten' if write else '(dry run — --write 로 반영)')


if __name__ == '__main__':
    main()
