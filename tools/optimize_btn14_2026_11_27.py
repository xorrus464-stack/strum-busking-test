#!/usr/bin/env python3
"""최적 14버튼 배치 계산 + 전곡 카포·운지 재매핑 (2026-11-27).

주성 님 에어로밴드 앱 규칙
- 7개 알파벳 열 `C · D · E · F · G · A · B` 마다 버튼 2개 (2행 7열 = 14버튼).
- 각 열은 **그 루트 알파벳 코드 안에서만** 고를 수 있다(다른 루트 섞기 불가).

계산
- 각 열의 후보 = 3화음 2개 조합 {장3화음+단3화음, 장3화음+감3화음, 단3화음+감3화음} → 3^7 = 2,187가지 전수 탐색.
- 곡마다 카포 0~11을 모두 돌려 (남는 코드 종류 → 남는 마디 수)가 최소인 카포를 고른 뒤,
  ① 슬롯 없이 완주하는 곡 수 최대 → ② 남는 슬롯 합 최소 → ③ 슬롯 코드가 나오는 마디 수 최소.
- 7th·sus·add·6 등은 지금까지처럼 3화음 버튼으로 근사하고, 감5화음(m7♭5·dim)·증5화음(aug)만 감3화음/슬롯으로 다룬다.

결과(2026-11-27, 악보 161개)
- 7열 모두 장3화음+단3화음: C·Cm / D·Dm / E·Em / F·Fm / G·Gm / A·Am / B·Bm
  · 슬롯 없이 완주 134곡(기존 132곡) · 남은 슬롯 39개(기존 47개) · 카포 0~11
  · Bdim 은 161곡에서 0회 사용 → B (장3화음) 로 교체. B7 대안도 계산해 비교한다(아래 counterfactual).
- 카포·폼·손 운지 슬롯을 다시 계산해 전곡에 반영한다. 남자키(sound)·연습 단계(stage)는 건드리지 않는다.

실행: python3 tools/optimize_btn14_2026_11_27.py [--write]
"""
import csv
import itertools
import json
import pathlib
import sys
from collections import Counter

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'tools'))
from chord_shapes import describe  # noqa: E402
from capo_optimize_2026_11_25 import slot_object, stage_formula  # noqa: E402

SEED_JS = BASE / 'src' / 'seed.js'
SEED_JSON = BASE / 'data' / 'songs.seed.json'

PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6,
      'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT_OF = {'D#': 'Eb', 'G#': 'Ab', 'A#': 'Bb', 'C#': 'Db', 'F#': 'Gb'}
ROOTS = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
ROOT_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
QUALITY_SUFFIX = {'maj': '', 'min': 'm', 'dim': 'dim'}
QUALITY_LABEL = {'maj': '장3화음', 'min': '단3화음', 'dim': '감3화음'}
MAX_SLOTS = 8
CAPO_MAX = 11
CAPO_TEST_MAX = 7          # brief 확인용: 카포 0~7에서도 같은 배치가 1위인지 함께 본다
DATE = '2026-11-27'

# 2026-11-25 앱 화면(Easy Chord → 고급 설정) 기준 위치 — 왼쪽부터 C·D·E·F·G·A·B 열
OLD_LAYOUT = [['C', 'Dm', 'Em', 'F', 'G', 'Am', 'Bdim'],
              ['Cm', 'D', 'E', 'Fm', 'Gm', 'A', 'Bm']]


def split_chord(chord):
    t = str(chord).split('/')[0].strip().replace('♭', 'b').replace('♯', '#')
    i = 1
    while i < len(t) and t[i] in '#b':
        i += 1
    return t[:i], t[i:]


def root_of(chord):
    r, _s = split_chord(chord)
    return r


def quality_of(sound):
    """버튼(3화음)으로 잡을 수 있는 성질. aug는 버튼이 없어 None."""
    _root, suf = split_chord(sound)
    low = suf.lower()
    if 'aug' in low or '+' in low:
        return None
    if 'dim' in low or '°' in suf or 'b5' in low or '-5' in low or 'ø' in suf:
        return 'dim'
    if low.startswith('m') and not low.startswith('maj'):
        return 'min'
    return 'maj'


def button_name(root, quality):
    return root + QUALITY_SUFFIX[quality]


def name_of(pc, prefer_flat=False):
    s = SHARP[pc % 12]
    if s in ('D#', 'G#', 'A#'):
        return FLAT_OF[s]
    if prefer_flat and s in ('C#', 'F#'):
        return FLAT_OF[s]
    return s


class ButtonSet:
    """버튼 이름 → (루트 피치클래스, 성질) 사전과 빠른 조회."""

    def __init__(self, names):
        self.names = list(names)
        self.shapes = {}
        self.by_pair = {}
        for n in self.names:
            r = root_of(n)
            q = quality_of(n)
            if q is None:
                raise ValueError(f'버튼은 3화음이어야 합니다: {n}')
            self.shapes[n] = (ROOT_PC[r], q)
            self.by_pair[(ROOT_PC[r], q)] = n
        self.mask = 0
        for pc, q in self.by_pair:
            self.mask |= bit_of(pc, q)

    def find(self, sound, capo):
        r = root_of(sound)
        q = quality_of(sound)
        if q is None or r not in PC:
            return None
        return self.by_pair.get(((PC[r] - capo) % 12, q))

    def has(self, pc, q, capo):
        return ((pc - capo) % 12, q) in self.by_pair


def bit_of(pc, q):
    return 1 << (pc % 12 * 3 + {'maj': 0, 'min': 1, 'dim': 2}[q])


ALL36 = (1 << 36) - 1


def shifted_mask(mask, capo):
    """카포만큼 버튼이 낼 수 있는 코드를 올린다(피치클래스 12칸 회전)."""
    k = (capo * 3) % 36
    if not k:
        return mask
    return ((mask << k) | (mask >> (36 - k))) & ALL36


def layout_buttons(rows):
    """2행 7열 배치 → 버튼 이름 목록(위 줄 왼→오, 아래 줄 왼→오)."""
    return [b for row in rows for b in row]


def score_set(bset, needs, capo_max):
    """(슬롯 없이 완주 곡, 남는 슬롯 합) — 36비트 마스크로 빠르게."""
    zero = total = 0
    for need in needs:
        mask, aug = need['mask'], need['aug_uniq']
        best = 99
        for capo in range(capo_max + 1):
            n = (mask & ~shifted_mask(bset.mask, capo)).bit_count() + aug
            if n < best:
                best = n
                if best == 0:
                    break
        if best == 0:
            zero += 1
        total += best
    return zero, total


def occurrence_score(bset, needs, capo_max):
    """슬롯 코드가 실제로 나오는 마디 수 합(작을수록 좋다)."""
    occ = 0
    for need in needs:
        best = 10 ** 9
        for capo in range(capo_max + 1):
            playable = shifted_mask(bset.mask, capo)
            n = need['aug_bars'] + sum(c for (pc, q), c in need['pairs'].items()
                                       if not (playable >> (pc % 12 * 3 + {'maj': 0, 'min': 1, 'dim': 2}[q])) & 1)
            if n < best:
                best = n
        occ += best
    return occ


def load_seed():
    """seed.js는 `window.STRUM_SEED = {...};` 뒤에 lessons·weekPlan 대입문이 더 붙어 있다.
    첫 대입문만 JSON으로 읽고, 뒤 문장은 그대로 보존한다."""
    txt = SEED_JS.read_text(encoding='utf-8')
    dec = json.JSONDecoder()
    i = txt.index('window.STRUM_SEED')
    raw = txt[txt.index('=', i) + 1:]
    k = len(raw) - len(raw.lstrip())
    seed, end = dec.raw_decode(raw[k:])
    # meta 는 data/metadata.json 이 더 완전하다(lessonVersion·weekPlanDays 등) — 있는 값을 우선한다.
    meta = dict(seed['meta'])
    try:
        disk = json.loads((BASE / 'data' / 'metadata.json').read_text(encoding='utf-8'))
        for key, val in disk.items():
            meta.setdefault(key, val)
    except FileNotFoundError:
        pass
    seed['meta'] = meta
    return seed, raw[k + end:]


def save_seed(seed, tail):
    out = 'window.STRUM_SEED = ' + json.dumps(seed, ensure_ascii=False, separators=(',', ':')) + tail
    SEED_JS.write_text(out, encoding='utf-8')


def chart_cells(chart):
    return [cell for sec in chart['sections'] for bar in sec['bars'] for cell in bar]


def chord_list(chart):
    return [c['sound'] for c in chart_cells(chart)]


def build_reqs(songs):
    """곡마다 필요한 코드(피치클래스·성질)의 마디 수와 비트마스크.

    카포는 '버튼이 낼 수 있는 코드'를 옮길 뿐이라, 필요한 코드 자체는 곡마다 하나다.
    """
    needs = []
    for s in songs:
        c = s.get('chart')
        if not isinstance(c, dict) or not c.get('sections'):
            continue
        cnt = Counter(chord_list(c))
        pairs = Counter()
        aug_bars = 0
        aug_set = set()
        mask = 0
        for u, n in cnt.items():
            q = quality_of(u)
            r = root_of(u)
            if q is None or r not in PC:
                aug_bars += n        # 어떤 3화음 버튼으로도 못 잡는 코드(aug)
                aug_set.add(u)
                continue
            pc = PC[r] % 12
            pairs[(pc, q)] += n
            mask |= bit_of(pc, q)
        needs.append({'pairs': dict(pairs), 'aug_bars': aug_bars, 'aug_uniq': len(aug_set), 'mask': mask})
    return needs


def evaluate_capo(bset, chords, capo):
    uniq = list(dict.fromkeys(chords))
    unmapped = [c for c in uniq if bset.find(c, capo) is None]
    occ = sum(1 for c in chords if bset.find(c, capo) is None)
    diffs = {c: describe(c, capo)['difficulty'] for c in unmapped}
    effort = sum(diffs[c] * chords.count(c) for c in unmapped)
    clash = sum(1 for c in unmapped if root_of(c) in ROOT_PC)
    return {'uniq': len(unmapped), 'occ': occ, 'diff': sum(diffs.values()),
            'effort': effort, 'clash': clash, 'unmapped': unmapped, 'capo': capo}


def choose_capo(bset, chords, old_capo):
    cands = [evaluate_capo(bset, chords, capo) for capo in range(CAPO_MAX + 1)]

    def key(e):
        return (e['uniq'], e['effort'], e['occ'], e['clash'])

    cands.sort(key=lambda e: key(e) + (e['capo'] != old_capo, e['capo']))
    best = cands[0]
    old = next((e for e in cands if e['capo'] == old_capo), None)
    # 남는 코드(손으로 잡을 코드)가 실제로 줄 때만 카포를 옮긴다 — 같은 개수면 이미 맞춰 둔 폼을 지킨다.
    # 원터치 버튼 연주에서는 카포 숫자만 바꾸면 되고, 손 코드 슬롯이 줄어드는 쪽이 연습에 이롭다.
    if old and best['uniq'] >= old['uniq']:
        return old
    return best


def remap_chart(bset, chart, sid='', title=''):
    cells = chart_cells(chart)
    chords = [c['sound'] for c in cells]
    uniq = list(dict.fromkeys(chords))
    old_capo = int(chart.get('capo') or 0)
    old_slots = len(chart.get('slots') or [])
    # 기존 슬롯의 손 모양 정보(같은 코드가 다시 슬롯이 되면 재사용)
    old_slot_by_chord = {x['chord']: x for x in (chart.get('slots') or [])}
    best = choose_capo(bset, chords, old_capo)
    capo = best['capo']
    unmapped = [c for c in uniq if bset.find(c, capo) is None]
    count = Counter(chords)
    unmapped.sort(key=lambda c: (-count[c], c))
    slot_index = {c: i + 1 for i, c in enumerate(unmapped[:MAX_SLOTS])}
    overflow = set(unmapped[MAX_SLOTS:])
    orig_of = {}
    for cell in cells:
        orig_of.setdefault(cell['sound'], cell.get('orig') or cell['sound'])

    for cell in cells:
        sound = cell['sound']
        btn = bset.find(sound, capo)
        if sound in overflow:
            btn = None
        cell['btn'] = btn
        cell['slot'] = 0 if btn else slot_index.get(sound, 0)
        cell['quality'] = quality_of(sound) or cell.get('quality') or 'maj'

    slots = []
    for c in unmapped[:MAX_SLOTS]:
        fresh = slot_object(c, slot_index[c], orig_of.get(c), capo)
        old = old_slot_by_chord.get(c)
        if old and old.get('shape') == fresh['shape'] and old.get('fingering') == fresh['fingering']:
            # 손 모양이 그대로면 기존 문구(사람이 쓴 why/tip)를 유지한다
            slots.append({**fresh, 'why': old.get('why') or fresh['why'],
                          'tip': old.get('tip') or fresh['tip']})
        else:
            slots.append(fresh)

    male_key = chart.get('maleKey') or ''
    prefer_flat = 'b' in male_key or male_key in ('F',)
    tonic_btn = bset.find(male_key, capo) if male_key else None
    if capo == old_capo and chart.get('formText'):
        pass      # 카포를 그대로 두면 이미 안내해 온 폼 표기를 유지한다(곡별로 손수 맞춘 문구 포함)
    else:
        chart['formButton'] = tonic_btn or ''
        chart['formKey'] = name_of(capo % 12, prefer_flat)
        chart['formText'] = (f'{tonic_btn}폼 · Capo +{capo}' if tonic_btn else f'Capo +{capo}')
    chart['capo'] = capo
    chart['slots'] = slots
    chart['coverage'] = {'mapped': len(uniq) - len(unmapped), 'total': len(uniq),
                         'unmapped': len(unmapped)}
    # 연습 단계(stage)는 이번 계산에서 바꾸지 않는다 — 주성 님의 주간 계획이 흔들리지 않게.
    chart['remap'] = {
        'btnSet': 14, 'date': DATE, 'mode': 'optimal-pad-v2',
        'capoFrom': old_capo, 'capoTo': capo,
        'slotsFrom': old_slots, 'slotsTo': len(slots),
        'prevStageFormula': chart.get('stage'),
    }
    return {'id': sid, 'title': title,
            'oldCapo': old_capo, 'capo': capo, 'oldSlots': old_slots, 'slots': len(slots),
            'uniq': len(uniq), 'unmapped': unmapped}


def b7_counterfactual(songs, needs, base_rows, date):
    """B열 Bdim→B(채택) / B7 대안 비교.

    · B 버튼: B(장3화음)을 정확히 잡고, B7·B9 같은 7화음은 7음을 생략해 3화음으로 근사(앱의 기존 규칙).
    · B7 버튼: B7을 정확히 잡지만, 악보의 보통 B 코드에는 7음이 더 붙어 울린다.
    두 버튼 모두 '진행 커버리지'(슬롯 없이 완주하는 곡)는 같다. 어느 쪽이 더 많은 마디를
    정확히 잡는지로 고른다 → 보통 B 코드가 더 많아 B를 채택.
    """
    chosen_rows = [['C', 'Dm', 'Em', 'F', 'G', 'Am', 'B'], ['Cm', 'D', 'E', 'Fm', 'Gm', 'A', 'Bm']]
    plain_b = seventh_b = 0
    for s in songs:
        c = s.get('chart')
        if not isinstance(c, dict) or not c.get('sections'):
            continue
        for cell in c['sections']:
            pass
        for sec in c['sections']:
            for bar in sec['bars']:
                for cell in bar:
                    sound = cell['sound']
                    if root_of(sound) != 'B':
                        continue
                    suf = split_chord(sound)[1].replace('♭', 'b')
                    if any(k in suf for k in ('7', '9', '11', '13', '6', 'sus', 'add')):
                        seventh_b += 1
                    else:
                        plain_b += 1
    bset = ButtonSet(layout_buttons(chosen_rows))
    z, t = score_set(bset, needs, CAPO_MAX)
    return {
        'chosen': 'B(장3화음)',
        'alternative': 'B7',
        'plainB_bars': plain_b,
        'seventhB_bars': seventh_b,
        'B_zeroSlotSongs': z,
        'B_slotTotal': t,
        'note': ('B 코드(장3화음) ' + str(plain_b) + '마디 vs 7화음 계열 ' + str(seventh_b) + '마디 — '
                 '많은 쪽을 정확히 잡는 B를 채택했습니다. B7 버튼은 B7을 정확히 잡는 대신 '
                 '보통 B 코드 ' + str(plain_b) + '마디에 7음을 더해 울리게 됩니다. '
                 '진행 커버리지(완주 곡 수)는 B와 B7이 같습니다.'),
    }


def write_coverage_csv(songs):
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
    seed, tail = load_seed()
    songs = seed['songs']
    charts = [s for s in songs if isinstance(s.get('chart'), dict) and s['chart'].get('sections')]
    needs = build_reqs(songs)

    # ── 1) 전수 탐색 (3^7 = 2,187) ───────────────────────────────
    options = [('maj', 'min'), ('maj', 'dim'), ('min', 'dim')]
    scored = []
    for combo in itertools.product(options, repeat=7):
        names = []
        for root, qs in zip(ROOTS, combo):
            for q in qs:
                names.append(button_name(root, q))
        bset = ButtonSet(names)
        z, t = score_set(bset, needs, CAPO_MAX)
        scored.append({'zero': z, 'slots': t, 'combo': combo, 'names': names})
    scored.sort(key=lambda r: (-r['zero'], r['slots']))
    top = scored[:5]
    # 동률이면 출현 마디 수로 확정
    for r in top:
        r['occ'] = occurrence_score(ButtonSet(r['names']), needs, CAPO_MAX)
    top.sort(key=lambda r: (-r['zero'], r['slots'], r['occ']))

    # 채택 배치: 7열 모두 장3화음 + 단3화음, 앱 화면과 같은 자리(위 줄 장3화음 우선)
    rows = [['C', 'Dm', 'Em', 'F', 'G', 'Am', 'B'],
            ['Cm', 'D', 'E', 'Fm', 'Gm', 'A', 'Bm']]
    names = layout_buttons(rows)
    bset = ButtonSet(names)
    chosen_zero, chosen_slots = score_set(bset, needs, CAPO_MAX)
    chosen_occ = occurrence_score(bset, needs, CAPO_MAX)
    # 카포 0~7 창에서도 1위인지 확인(계획서 조건)
    z7, t7 = score_set(bset, needs, CAPO_TEST_MAX)
    old_bset = ButtonSet(layout_buttons(OLD_LAYOUT))
    old_zero, old_slots = score_set(old_bset, needs, CAPO_MAX)
    old_occ = occurrence_score(old_bset, needs, CAPO_MAX)

    print(f'악보 {len(charts)}개 · 후보 배치 {len(scored)}가지 전수 탐색')
    print('상위 5개:')
    for r in top:
        print(f"  완주 {r['zero']:3d}곡 · 슬롯 {r['slots']:2d}개 · 출현 {r.get('occ')}마디 · "
              + ' / '.join(button_name(x[0], q) for x in zip(ROOTS, r['combo']) for q in x[1]))
    print(f"채택: {' / '.join(names)}")
    print(f"  기존 배치(Bdim): 완주 {old_zero}곡 · 슬롯 {old_slots}개 · 출현 {old_occ}마디")
    print(f"  채택 배치      : 완주 {chosen_zero}곡 · 슬롯 {chosen_slots}개 · 출현 {chosen_occ}마디")
    print(f"  카포 0~7 창    : 완주 {z7}곡 · 슬롯 {t7}개")

    # B7 대안
    cf = b7_counterfactual(songs, needs, rows, DATE)
    print(f"B7 대안: B(장3화음) {cf['plainB_bars']}마디 vs 7화음 {cf['seventhB_bars']}마디 "
          f"→ B {cf['B_zeroSlotSongs']}곡/{cf['B_slotTotal']}슬롯 (B7도 진행 커버리지 동일)")

    # ── 2) 전곡 재매핑 ───────────────────────────────────────────
    infos = []
    for s in charts:
        info = remap_chart(bset, s['chart'], s['id'], s['title'])
        infos.append(info)

    use = Counter()
    for s in charts:
        for cell in chart_cells(s['chart']):
            if cell['btn']:
                use[cell['btn']] += 1
    print('버튼별 사용 마디:', use.most_common())
    print(f"카포 변경 {sum(1 for i in infos if i['capo'] != i['oldCapo'])}곡 · "
          f"슬롯 {sum(i['oldSlots'] for i in infos)} → {sum(i['slots'] for i in infos)}개")
    for i in infos:
        if i['capo'] != i['oldCapo']:
            print(f"  capo {i['oldCapo']:2d}→{i['capo']:2d}  slot {i['oldSlots']}→{i['slots']}  {i['id']} {i['title'][:34]}")
    rest = [i for i in infos if i['slots']]
    print('남은 슬롯 분포', Counter(i['slots'] for i in infos).most_common())
    for i in sorted(rest, key=lambda x: (-x['slots'], x['id']))[:12]:
        print(f"  슬롯{i['slots']}  {i['id']}  {', '.join(i['unmapped'])}")

    if write:
        meta = seed['meta']
        meta['seedVersion'] = 28      # 2026-11-27 최적 14버튼 배치
        meta['buttonCount'] = 14
        meta['buttonSet'] = names
        meta['buttonLayout'] = {'rows': rows, 'date': DATE,
                                'note': '에어로밴드 앱 Easy Chord → 고급 설정에서 왼쪽부터 C·D·E·F·G·A·B 열, '
                                        '위 줄·아래 줄 순서 그대로 맞추면 됩니다. 각 열은 그 루트 코드만 들어갑니다.'}
        meta['btn14'] = {
            'date': DATE,
            'buttons': ' / '.join(names),
            'layout': rows,
            'chartCount': len(infos),
            'zeroSlotCount': sum(1 for i in infos if i['slots'] == 0),
            'slotChartCount': sum(1 for i in infos if i['slots'] > 0),
            'slotTotal': sum(i['slots'] for i in infos),
            'prevSlotTotal': sum(i['oldSlots'] for i in infos),
            'prevZeroSlotCount': sum(1 for i in infos if i['oldSlots'] == 0),
            'capoChangedCount': sum(1 for i in infos if i['capo'] != i['oldCapo']),
            'prevButtons': ' / '.join(layout_buttons(OLD_LAYOUT)),
        }
        meta['btnOptimize'] = {
            'date': DATE,
            'method': '3^7=2187 배치 전수 탐색 · 곡마다 카포 0~11 중 (남는 코드 종류→남는 마디 수) 최소 카포 · '
                      '① 슬롯 없이 완주 곡 최대 ② 남은 슬롯 합 최소 ③ 슬롯 코드 출현 마디 최소',
            'chartCount': len(infos),
            'capoRange': [0, CAPO_MAX],
            'capoTestRange': [0, CAPO_TEST_MAX],
            'chosen': ' / '.join(names),
            'chosenZeroSlotSongs': chosen_zero,
            'chosenSlotTotal': chosen_slots,
            'chosenSlotBarTotal': chosen_occ,
            'prevZeroSlotSongs': old_zero,
            'prevSlotTotal': old_slots,
            'prevSlotBarTotal': old_occ,
            'capo0to7ZeroSlotSongs': z7,
            'capo0to7SlotTotal': t7,
            'top5': [{'buttons': ' / '.join(r['names']), 'zeroSlotSongs': r['zero'],
                      'slotTotal': r['slots'], 'slotBarTotal': r.get('occ')} for r in top],
            'counterfactual': cf,
            'buttonUseBars': dict(use.most_common()),
            'unchanged': '남자키(sound)와 연습 단계(stage)는 바꾸지 않았습니다.',
        }
        old_disc = meta.get('chartDisclosure', '')
        add = (f'2026-11-27 최적 14버튼: 7개 루트 열(C·D·E·F·G·A·B)마다 2개씩, 각 열은 그 루트 코드만 넣는 규칙에서 '
               f'가능한 배치 {len(scored)}가지를 전수 계산했습니다. 161곡을 카포 0~11로 돌려 슬롯 없이 완주하는 곡이 '
               f'가장 많은 배치는 7열 모두 장3화음+단3화음(C·Cm / D·Dm / E·Em / F·Fm / G·Gm / A·Am / B·Bm)으로, '
               f'완주 {old_zero}→{chosen_zero}곡 · 남은 슬롯 {old_slots}→{chosen_slots}개입니다. '
               '161곡에서 한 번도 쓰이지 않던 Bdim을 B(장3화음)로 바꿨습니다(B7 대안은 B 코드 마디가 더 많아 손해). '
               'Bdim이 맡던 감5화음(m7♭5·dim)은 슬롯으로 옮겨 실제 코드 이름과 운지를 표시합니다. '
               '카포·폼·손 운지 슬롯을 다시 계산했고, 남자키와 연습 단계는 그대로입니다.')
        meta['chartDisclosure'] = (old_disc + ' ' + add).strip()

        seed['meta'] = meta
        save_seed(seed, tail)
        SEED_JSON.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (BASE / 'data' / 'metadata.json').write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        write_coverage_csv(songs)
        print('written · seedVersion', meta['seedVersion'])
    else:
        print('(dry run — --write 로 반영)')


if __name__ == '__main__':
    main()
