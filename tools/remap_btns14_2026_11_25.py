#!/usr/bin/env python3
"""에어로밴드 Easy Chord 고급 설정 14버튼(2행 7열) 기준으로 악보를 재매핑한다.

2026-11-25 주성 님이 보낸 에어로밴드 앱 실제 화면(고급 설정)으로 확인한 버튼:
  윗줄: C · Dm · Em · F · G · Am · Bdim
  아랫줄: Cm · D · E · Fm · Gm · A · Bm
기존 10버튼에 Am·A·Bm·Bdim 4개가 늘었으므로, 곡마다 Capo(0~7)를 다시 골라
SimplifyChord 슬롯을 최소화하고 남는 슬롯만 남긴다.

원칙
- maleKey(남자키)와 각 마디의 sound(실제 울리는 코드)는 절대 바꾸지 않는다.
  카포는 모양(폼)만 옮기므로 소리는 그대로다.
- 카포는 (① 슬롯에 들어가는 서로 다른 코드 수 → ② 기존 카포 유지 →
  ③ 슬롯이 나오는 마디 수 → ④ 낮은 카포) 순으로 최소가 되는 값을 고른다.
  (기존 카포로도 슬롯이 더 줄지 않으면 그대로 둬서, 이미 맞춰 둔 카포를 함부로 바꾸지 않는다.)
- 7th·maj7·m7·6·sus4·add9은 지금까지처럼 3화음 버튼으로 근사한다.
  m7b5·m7-5·dim7처럼 감5화음이 들어간 코드는 Bdim 버튼(3화음)으로 근사한다.
  aug(증5화음)는 3화음으로 대신할 수 없어 슬롯으로 남긴다.
- stage(연습 단계)는 이번 재매핑으로 슬롯이 실제로 줄어 근거가 약해진 곡만 한 단계 내린다.
  (올리지 않고, 슬롯 수가 그대로인 곡의 기존 단계는 건드리지 않는다. 퍼커시브·1단계도 그대로.)

실행: python3 tools/remap_btns14_2026_11_25.py [--write]
      --write 없이 실행하면 바뀔 내용만 집계해 보여준다.
"""
import json
import re
import sys
import pathlib
from collections import Counter

BASE = pathlib.Path(__file__).resolve().parents[1]
SEED_JS = BASE / 'src' / 'seed.js'
SEED_JSON = BASE / 'data' / 'songs.seed.json'

PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6,
      'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT_OF = {'D#': 'Eb', 'G#': 'Ab', 'A#': 'Bb', 'C#': 'Db', 'F#': 'Gb'}

# 14버튼 — 화면 순서 그대로(윗줄 7 + 아랫줄 7)
BTNS14 = ['C', 'Dm', 'Em', 'F', 'G', 'Am', 'Bdim', 'Cm', 'D', 'E', 'Fm', 'Gm', 'A', 'Bm']
SHAPES = {'C': (0, 'maj'), 'D': (2, 'maj'), 'E': (4, 'maj'), 'F': (5, 'maj'), 'G': (7, 'maj'),
          'A': (9, 'maj'),
          'Cm': (0, 'min'), 'Dm': (2, 'min'), 'Em': (4, 'min'), 'Fm': (5, 'min'), 'Gm': (7, 'min'),
          'Am': (9, 'min'), 'Bm': (11, 'min'),
          'Bdim': (11, 'dim')}
MAX_SLOTS = 8

# 슬롯에 남는 코드의 약식 대안(사실 기반 제안, 연주자 선택)
EASY_ALT = {
    'B': 'B7(x21202) 약식', 'Bb': 'Bb(6프렛 바레)', 'Bbm': 'Bbm7(x13121)',
    'F#': 'F#(244322)', 'F#m': 'F#m(244222)', 'F#m7': 'F#m7(242222)',
    'C#m': 'C#m7(x46454)', 'C#m7': 'C#m7(x46454)', 'G#': 'G#7(464544)', 'G#m': 'G#m7(464444)',
    'Ab': 'Ab(466544)', 'Abm': 'Abm7(464444)', 'Db': 'Db(x46664)', 'Dbm': 'Dbm(x46664)',
    'Eb': 'Eb(x68886)', 'Ebm': 'Ebm7(x68676)', 'A#m': 'A#m7(x13121)',
    'Faug': 'F7(xx3241) 근사 또는 Fmaj7', 'Abaug': 'Ab7(464544) 근사',
    'Bbm7b5': 'Bbm7♭5(x13121 바레)', 'Bm7b5': 'Bm7♭5(x20202 근사)',
    'B9sus4': 'B7sus4(x22202)', 'D/F#': 'D(2프렛 바레) 또는 D/F#', 'E/G#': 'E(022100)',
    'C/E': 'C(x32010)', 'F/A': 'F(133211)', 'Am6': 'Am(x02010)', 'Am7': 'Am7(x02010)',
}


def split_chord(chord):
    t = str(chord).split('/')[0].strip()
    i = 1
    while i < len(t) and t[i] in '#b':
        i += 1
    return t[:i], t[i:]


def quality_of(sound):
    """버튼으로 칠 수 있는 3화음 성질. aug는 버튼이 없어 None."""
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
        bp, bq = SHAPES[btn]
        if bq == q and (bp + capo) % 12 == pc:
            return btn
    return None


def name_of(pc, prefer_flat=False):
    """기존 build_charts.name()과 같은 표기 규칙(장조 이명은 ♭, b 표기 곡만 C#·F#도 ♭)."""
    s = SHARP[pc % 12]
    if s in ('D#', 'G#', 'A#'):
        return FLAT_OF[s]
    if prefer_flat and s in ('C#', 'F#'):
        return FLAT_OF[s]
    return s


def stage_formula(total_unique, slots):
    return 1 if total_unique <= 4 else (2 if total_unique <= 6 and slots <= 1 else 3)


def choose_capo(chords, old_capo):
    """슬롯을 최소로 하는 카포를 고른다.

    카포를 바꾸면 그동안 맞춰 둔 폼이 달라지므로, 기존 카포가 쓸 만하면 그대로 둔다.
    기존 카포를 버리는 경우: (a) 다른 카포에서 슬롯 없이 완주(0개)가 가능해졌거나,
    (b) 남는 슬롯이 2개 이상 줄 때만.
    """
    uniq = list(dict.fromkeys(chords))
    scored = []
    for capo in range(0, 8):
        unmapped = [c for c in uniq if find_button(c, capo) is None]
        occ = sum(1 for c in chords if find_button(c, capo) is None)
        scored.append((len(unmapped), capo, occ, unmapped))
    best_unm = min(x[0] for x in scored)
    keep = [x for x in scored if x[1] == old_capo] if old_capo in range(0, 8) else []
    if keep:
        old = keep[0]
        keep_it = not ((best_unm == 0 and old[0] > 0) or (best_unm <= old[0] - 2))
        if keep_it:
            return old[1], old[3]
    pool = [x for x in scored if x[0] == best_unm]
    pool.sort(key=lambda x: (x[1] != old_capo, x[2], x[1]))
    return pool[0][1], pool[0][3]


def remap_chart(chart):
    chords = [cell['sound'] for sec in chart['sections'] for bar in sec['bars'] for cell in bar]
    uniq = list(dict.fromkeys(chords))
    old_capo = chart.get('capo')
    old_slots = len(chart.get('slots') or [])
    old_alt = {s['chord']: s.get('alt', '') for s in (chart.get('slots') or [])}
    capo, unmapped = choose_capo(chords, old_capo)

    slot_index = {}
    for c in unmapped[:MAX_SLOTS]:
        slot_index[c] = len(slot_index) + 1
    overflow = set(unmapped[MAX_SLOTS:])

    for sec in chart['sections']:
        for bar in sec['bars']:
            for cell in bar:
                sound = cell['sound']
                btn = find_button(sound, capo)
                if sound in overflow:
                    btn = None
                q = quality_of(sound) or cell.get('quality')
                if btn is None:
                    cell['btn'] = None
                    cell['slot'] = slot_index.get(sound, 0)
                    cell['quality'] = q
                else:
                    cell['btn'] = btn
                    cell['slot'] = 0
                    cell['quality'] = q

    slots = []
    for c, n in slot_index.items():
        slots.append({
            'slot': n,
            'chord': c,
            'orig': next((cell['orig'] for sec in chart['sections'] for bar in sec['bars']
                          for cell in bar if cell['sound'] == c), c),
            'alt': old_alt.get(c) or EASY_ALT.get(c, '') or EASY_ALT.get(split_chord(c)[0], ''),
            'why': '원터치 14버튼에도 없는 코드(증5화음·반음계 등)',
        })

    # 으뜸화음(남자키) 버튼 — 폼 안내
    male_key = chart.get('maleKey') or ''
    prefer_flat = 'b' in male_key or male_key in ('F',)
    tonic_btn = find_button(male_key, capo) if male_key else None
    chart['capo'] = capo
    chart['slots'] = slots
    chart['formButton'] = tonic_btn or ''
    chart['formKey'] = name_of(capo % 12, prefer_flat)
    chart['formText'] = (f'{tonic_btn}폼 · Capo +{capo}' if tonic_btn else f'Capo +{capo}')
    chart['coverage'] = {'mapped': len(uniq) - len(unmapped), 'total': len(uniq), 'unmapped': len(unmapped)}

    # stage: 슬롯이 줄어 근거가 약해진 곡만 내린다(올리지 않음). 퍼커시브·1단계는 유지.
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
        'btnSet': 14,
        'date': '2026-11-25',
        'fromCapo': old_capo,
        'fromSlots': old_slots,
        'toCapo': capo,
        'toSlots': len(slots),
    }
    return {
        'id': chart.get('id'),
        'oldCapo': old_capo, 'capo': capo, 'oldSlots': old_slots, 'slots': len(slots),
        'oldStage': cur_stage, 'stage': new_stage, 'uniq': len(uniq),
        'unmapped': unmapped, 'slotChords': [s['chord'] for s in slots],
    }


def load_seed():
    txt = SEED_JS.read_text(encoding='utf-8')
    head = 'window.STRUM_SEED = '
    i = txt.index(head) + len(head)
    body = txt[i:].rstrip()
    assert body.endswith(';')
    return json.loads(body[:-1].rstrip())


def main():
    write = '--write' in sys.argv
    seed = load_seed()
    songs = seed['songs']
    if write and 'btn14' in seed['meta'] and '--force' not in sys.argv:
        # 이미 반영된 시드: 재계산(슬롯·카포 이력 중복) 없이 데이터 파일만 다시 맞춘다.
        SEED_JSON.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (BASE / 'data' / 'metadata.json').write_text(
            json.dumps(seed['meta'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('seedVersion', seed['meta']['seedVersion'], '· 이미 14버튼 반영됨 — 데이터 파일만 동기화')
        return
    rows = []
    for s in songs:
        c = s.get('chart')
        if not isinstance(c, dict) or not c.get('sections'):
            continue
        info = remap_chart(c)
        info['id'] = s['id']
        info['title'] = s['title']
        rows.append(info)

    if write:
        meta = seed['meta']
        meta['seedVersion'] = 22
        meta['chartVersion'] = '2026-11-25'
        meta['buttonCount'] = 14
        meta['buttonSet'] = BTNS14
        zero = [r for r in rows if r['slots'] == 0]
        meta['btn14'] = {
            'date': '2026-11-25',
            'buttons': ' / '.join(BTNS14),
            'chartCount': len(rows),
            'zeroSlotCount': len(zero),
            'slotChartCount': len(rows) - len(zero),
            'slotTotal': sum(r['slots'] for r in rows),
            'prevSlotTotal': sum(r['oldSlots'] for r in rows),
            'capoChangedCount': sum(1 for r in rows if r['capo'] != r['oldCapo']),
        }
        old_disc = meta.get('chartDisclosure', '')
        add = ('2026-11-25: 에어로밴드 앱 Easy Chord → 고급 설정 화면에서 확인한 실제 버튼 14개'
               '(C·Dm·Em·F·G·Am·Bdim / Cm·D·E·Fm·Gm·A·Bm)로 전곡 악보를 다시 매핑했습니다. '
               '기존 10버튼에서는 슬롯으로 빠지던 Am·A·Bm과 감5화음 계열(m7♭5)까지 버튼으로 잡히므로, '
               '곡마다 Capo(0~7)를 다시 골라 슬롯을 최소화했습니다. 남자키와 실제로 울리는 코드(sound)는 그대로입니다. '
               f'악보 {len(rows)}개 중 슬롯 없이 14버튼만으로 완주하는 곡이 {len(zero)}개, '
               f'남은 슬롯 합계 {sum(r["slots"] for r in rows)}개(이전 10버튼 기준 {sum(r["oldSlots"] for r in rows)}개)입니다. '
               '증5화음(aug)처럼 3화음 버튼으로 대신할 수 없는 코드만 SimplifyChord 슬롯(최대 8개)에 남겼습니다.')
        # 기존 문장 중 10버튼 서술만 새 기준으로 바꾼다.
        old_disc = old_disc.replace('원터치 버튼에 없는 코드는 SimplifyChord 슬롯(최대 8개)으로 안내합니다.',
                                    '원터치 14버튼에도 없는 코드는 SimplifyChord 슬롯(최대 8개)으로 안내합니다.')
        meta['chartDisclosure'] = (old_disc + ' ' + add).strip()

        out = 'window.STRUM_SEED = ' + json.dumps(seed, ensure_ascii=False, separators=(',', ':')) + ';\n'
        SEED_JS.write_text(out, encoding='utf-8')
        SEED_JSON.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (BASE / 'data' / 'metadata.json').write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    zero = [r for r in rows if r['slots'] == 0]
    print(f'악보 {len(rows)}개 · 슬롯 합계 {sum(r["oldSlots"] for r in rows)} → {sum(r["slots"] for r in rows)}')
    print(f'슬롯 0개(14버튼 완주): {sum(1 for r in rows if r["oldSlots"] == 0)} → {len(zero)}')
    print(f'카포 변경 {sum(1 for r in rows if r["capo"] != r["oldCapo"])}곡 · 단계 변경 {sum(1 for r in rows if r["stage"] != r["oldStage"])}곡')
    print('남은 슬롯', Counter(r['slots'] for r in rows).most_common())
    for r in rows:
        if r['capo'] != r['oldCapo']:
            print(f"  capo {r['oldCapo']}→{r['capo']}  slot {r['oldSlots']}→{r['slots']}  {r['id']} {r['title'][:40]}")
    for r in rows:
        if r['stage'] != r['oldStage']:
            print(f"  stage {r['oldStage']}→{r['stage']}  slot {r['oldSlots']}→{r['slots']}  {r['id']} {r['title'][:40]}")
    rest = [r for r in rows if r['slots']]
    print('\n슬롯이 남는 곡:')
    for r in sorted(rest, key=lambda x: -x['slots']):
        print(f"  {r['slots']}개  {r['id']}  {', '.join(r['slotChords'])}")
    print('written' if write else '(dry run — --write 로 반영)')


if __name__ == '__main__':
    main()
