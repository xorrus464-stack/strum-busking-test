#!/usr/bin/env python3
"""기타 코드 운지(보이싱) 엔진 — 실제 울리는 코드 이름에서 프렛·줄·손가락을 계산한다.

쓰임
- tools/capo_optimize_2026_11_25.py: 카포를 고를 때 '남는 코드의 손 모양이 얼마나 쉬운지'를 계산
- 악보 데이터(slot.fingering): 화면에서 그릴 SVG 코드 다이어그램 값

원칙
- 모든 보이싱은 실제 음정으로 검증한다(_check). 근음이 없거나 코드 구성음 밖의 음이 울리면 버린다.
  손가락 번호는 통상적인 오픈 코드/바레 폼을 그대로 쓴다.
- 프렛 값은 카포를 0프렛으로 본 상대 위치다(에어로밴드 버튼과 같은 기준).
- 줄 번호는 6번(가장 굵은 줄) → 1번(가장 얇은 줄) 순서. -1 = 뮤트(X), 0 = 개방현(O).
"""
PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6,
      'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11, 'Cb': 11, 'Fb': 4}
SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT_OF = {'D#': 'Eb', 'G#': 'Ab', 'A#': 'Bb', 'C#': 'Db', 'F#': 'Gb'}
OPEN_PC = [4, 9, 2, 7, 11, 4]        # 6번줄 → 1번줄 개방현 피치클래스 (E A D G B E)

INTERVALS = {
    'maj': [0, 4, 7], 'min': [0, 3, 7], 'dim': [0, 3, 6], 'aug': [0, 4, 8],
    '7': [0, 4, 7, 10], 'm7': [0, 3, 7, 10], 'maj7': [0, 4, 7, 11],
    'dim7': [0, 3, 6, 9], 'm7b5': [0, 3, 6, 10],
    '6': [0, 4, 7, 9], 'm6': [0, 3, 7, 9],
}
# 화면 표기(코드 이름 뒤에 붙는 글자)
FAMILY_LABEL = {'maj': '', 'min': 'm', 'dim': 'dim', 'aug': 'aug', '7': '7', 'm7': 'm7',
                'maj7': 'M7', 'dim7': 'dim7', 'm7b5': 'm7♭5', '6': '6', 'm6': 'm6',
                'sus4': 'sus4', 'sus2': 'sus2', 'add9': 'add9', '7sus4': '7sus4', '9': '9'}
# 텐션·특수 코드는 손 모양이 어려우므로 따로 표시
SPECIAL = {'aug', 'dim7', 'm7b5', 'dim', '9', '7sus4', 'add9', 'sus2', 'sus4', 'm6', '6'}

# ── 폼 템플릿 ──────────────────────────────────────────────────────────────
# deltas: 6번줄→1번줄, 근음 프렛 f 기준 상대 프렛(-9 = 뮤트)
# fingers/barre: f>=1(바레 폼), open_*: f==0(개방현 폼)
TEMPLATES = {
    'maj': [
        {'name': 'E폼', 'string': 6, 'deltas': [0, 2, 2, 1, 0, 0],
         'fingers': [1, 3, 4, 2, 1, 1], 'barre': (0, 6, 1),
         'open_fingers': [0, 2, 3, 1, 0, 0], 'open_barre': None},
        {'name': 'A폼', 'string': 5, 'deltas': [-9, 0, 2, 2, 2, 0],
         'fingers': [0, 1, 2, 3, 4, 1], 'barre': (0, 5, 1),
         'open_fingers': [0, 0, 1, 2, 3, 0], 'open_barre': None},
    ],
    'min': [
        {'name': 'Em폼', 'string': 6, 'deltas': [0, 2, 2, 0, 0, 0],
         'fingers': [1, 3, 4, 1, 1, 1], 'barre': (0, 6, 1),
         'open_fingers': [0, 2, 3, 0, 0, 0], 'open_barre': None},
        {'name': 'Am폼', 'string': 5, 'deltas': [-9, 0, 2, 2, 1, 0],
         'fingers': [0, 1, 3, 4, 2, 1], 'barre': (0, 5, 1),
         'open_fingers': [0, 0, 2, 3, 1, 0], 'open_barre': None},
    ],
    '7': [
        {'name': 'E7폼', 'string': 6, 'deltas': [0, 2, 0, 1, 0, 0],
         'fingers': [1, 3, 1, 2, 1, 1], 'barre': (0, 6, 1),
         'open_fingers': [0, 2, 0, 1, 0, 0], 'open_barre': None},
        {'name': 'A7폼', 'string': 5, 'deltas': [-9, 0, 2, 0, 2, 0],
         'fingers': [0, 1, 3, 1, 4, 1], 'barre': (0, 5, 1),
         'open_fingers': [0, 0, 2, 0, 3, 0], 'open_barre': None},
    ],
    'm7': [
        {'name': 'Em7폼', 'string': 6, 'deltas': [0, 2, 0, 0, 0, 0],
         'fingers': [1, 3, 1, 1, 1, 1], 'barre': (0, 6, 1),
         'open_fingers': [0, 2, 0, 0, 0, 0], 'open_barre': None},
        {'name': 'Am7폼', 'string': 5, 'deltas': [-9, 0, 2, 0, 1, 0],
         'fingers': [0, 1, 3, 1, 2, 1], 'barre': (0, 5, 1),
         'open_fingers': [0, 0, 2, 0, 1, 0], 'open_barre': None},
    ],
    'maj7': [
        {'name': 'Emaj7폼', 'string': 6, 'deltas': [0, 2, 1, 1, 0, 0],
         'fingers': [1, 3, 2, 4, 1, 1], 'barre': (0, 6, 1),
         'open_fingers': [0, 3, 1, 2, 0, 0], 'open_barre': None},
        {'name': 'Amaj7폼', 'string': 5, 'deltas': [-9, 0, 2, 1, 2, 0],
         'fingers': [0, 1, 3, 2, 4, 1], 'barre': (0, 5, 1),
         'open_fingers': [0, 0, 2, 1, 3, 0], 'open_barre': None},
    ],
    '6': [
        {'name': 'A6폼', 'string': 5, 'deltas': [-9, 0, 2, 2, 2, 2],
         'fingers': [0, 1, 3, 3, 3, 3], 'barre': (2, 4, 1),
         'open_fingers': [0, 0, 2, 2, 2, 2], 'open_barre': None},
    ],
    'm6': [
        {'name': 'Am6폼', 'string': 5, 'deltas': [-9, 0, 2, 2, 1, 2],
         'fingers': [0, 1, 3, 4, 2, 2], 'barre': None,
         'open_fingers': [0, 0, 2, 3, 1, 2], 'open_barre': None},
    ],
    'm7b5': [
        {'name': 'm7♭5폼(6번줄)', 'string': 6, 'deltas': [0, -9, 0, 0, -1, -9],
         'fingers': [1, 0, 2, 3, 4, 0], 'barre': None,
         'open_fingers': None, 'open_barre': None},
        {'name': 'm7♭5폼(5번줄)', 'string': 5, 'deltas': [-9, 0, 1, 0, 1, -9],
         'fingers': [0, 1, 3, 2, 4, 0], 'barre': None,
         'open_fingers': None, 'open_barre': None},
    ],
    'dim7': [
        {'name': 'dim7폼', 'string': 5, 'deltas': [-9, 0, 1, -1, 1, -9],
         'fingers': [0, 1, 3, 2, 4, 0], 'barre': None,
         'open_fingers': None, 'open_barre': None},
    ],
}

# 개방현 폼이 따로 있는 코드(바레 폼보다 훨씬 쉬움) — (근음 pc, 성질)
OPEN_EXTRA = {   # 개방현 폼 그대로(손가락 번호는 통상 운지)
    (11, '7'): {'name': 'B7 개방', 'frets': [-1, 2, 1, 2, 0, 2],
                'fingers': [0, 2, 1, 3, 0, 4], 'barre': None},
    (0, 'maj'): {'name': 'C 개방', 'frets': [-1, 3, 2, 0, 1, 0],
                 'fingers': [0, 3, 2, 0, 1, 0], 'barre': None},
    (7, 'maj'): {'name': 'G 개방', 'frets': [3, 2, 0, 0, 0, 3],
                 'fingers': [3, 2, 0, 0, 0, 4], 'barre': None},
    (2, 'maj'): {'name': 'D 개방', 'frets': [-1, -1, 0, 2, 3, 2],
                 'fingers': [0, 0, 0, 1, 3, 2], 'barre': None},
    (2, 'min'): {'name': 'Dm 개방', 'frets': [-1, -1, 0, 2, 3, 1],
                 'fingers': [0, 0, 0, 2, 3, 1], 'barre': None},
    (2, '7'): {'name': 'D7 개방', 'frets': [-1, -1, 0, 2, 1, 2],
               'fingers': [0, 0, 0, 2, 1, 3], 'barre': None},
    (7, '7'): {'name': 'G7 개방', 'frets': [3, 2, 0, 0, 0, 1],
               'fingers': [3, 2, 0, 0, 0, 1], 'barre': None},
    (0, '7'): {'name': 'C7 개방', 'frets': [-1, 3, 2, 3, 1, 0],
               'fingers': [0, 3, 2, 4, 1, 0], 'barre': None},
    (5, 'maj7'): {'name': 'Fmaj7 개방', 'frets': [-1, -1, 3, 2, 1, 0],
                  'fingers': [0, 0, 3, 2, 1, 0], 'barre': None},
    (0, 'maj7'): {'name': 'Cmaj7 개방', 'frets': [-1, 3, 2, 0, 0, 0],
                  'fingers': [0, 3, 2, 0, 0, 0], 'barre': None},
    (11, 'm7'): {'name': 'Bm7 개방', 'frets': [-1, 2, 0, 2, 0, 2],
                 'fingers': [0, 1, 0, 3, 0, 4], 'barre': None},   # 1번 손가락 5번줄 2프렛
    (11, 'min'): {'name': 'Bm 개방', 'frets': [-1, 2, 4, 4, 3, 2],
                  'fingers': [0, 1, 3, 4, 2, 1], 'barre': {'fret': 2, 'from': 1, 'to': 5, 'finger': 1}},
}


def parse(chord):
    """'B♭/C' 같은 이름 → {root, root_pc, family, suffix, bass, bass_pc}"""
    t = str(chord).strip().replace('♭', 'b').replace('♯', '#')
    bass = ''
    if '/' in t:
        t, bass = t.split('/', 1)
    i = 1
    while i < len(t) and t[i] in '#b':
        i += 1
    root, suf = t[:i], t[i:]
    s = suf
    low = s.lower().replace('∆', 'maj')
    if 'aug' in low or '+' in low:
        fam = 'aug'
    elif 'dim7' in low or '°7' in s:
        fam = 'dim7'
    elif 'm7b5' in low or 'm7-5' in low or 'm7♭5' in low or 'ø' in s:
        fam = 'm7b5'
    elif 'dim' in low or '°' in s:
        fam = 'dim'
    elif low in ('maj7', 'ma7', 'j7', 'm7+') or s in ('M7', 'Maj7', 'maj7'):
        fam = 'maj7'
    elif low in ('m7', 'min7'):
        fam = 'm7'
    elif low in ('m6', 'min6'):
        fam = 'm6'
    elif low in ('m', 'min', '-'):
        fam = 'min'
    elif low == '7sus4':
        fam = '7sus4'
    elif 'sus4' in low:
        fam = 'sus4'
    elif 'sus2' in low:
        fam = 'sus2'
    elif 'add9' in low or 'add2' in low:
        fam = 'add9'
    elif low == '6':
        fam = '6'
    elif low == '9':
        fam = '9'
    elif low == '7':
        fam = '7'
    else:
        fam = 'maj'   # 그 밖의 텐션은 3화음으로 근사
    return {'root': root, 'root_pc': PC[root], 'family': fam, 'suffix': suf,
            'bass': bass, 'bass_pc': PC[bass] if bass else None}


def shape_name(root_pc, family, prefer_flat=True):
    s = SHARP[root_pc % 12]
    if s in ('D#', 'G#', 'A#') or (prefer_flat and s in ('C#', 'F#')):
        s = FLAT_OF[s]
    return s + FAMILY_LABEL[family]


def chord_tones(root_pc, family):
    return {(root_pc + iv) % 12 for iv in INTERVALS.get(family, INTERVALS['maj'])}


def _check(frets, family, root_pc, bass_pc=None):
    """실제 음정 검증 — 코드 구성음 밖의 음이 있거나 근음이 없으면 탈락."""
    tones = chord_tones(root_pc, family)
    played = {(OPEN_PC[i] + fr) % 12 for i, fr in enumerate(frets) if fr is not None and fr >= 0}
    if not played <= tones:
        return False, '구성음 밖'
    if root_pc not in played:
        return False, '근음 없음'
    if family in ('maj', 'min', '7', 'm7', 'maj7', 'm7b5', '6', 'm6'):
        third = (root_pc + (3 if family in ('min', 'm7', 'm6', 'm7b5') else 4)) % 12
        if third not in played:
            return False, '3음 없음'
    if bass_pc is not None:
        for i, fr in enumerate(frets):
            if fr is not None and fr >= 0:
                if (OPEN_PC[i] + fr) % 12 != bass_pc:
                    return False, '베이스 불일치'
                break
    return True, ''


def voicing(root_pc, family):
    """(근음 pc, 성질)에 맞는 손 모양 후보를 쉬운 순서로 돌려준다."""
    out = []
    extra = OPEN_EXTRA.get((root_pc % 12, family))
    if extra:
        ok, _ = _check(extra['frets'], family, root_pc)
        if ok:
            out.append(_mk(extra['name'], extra['frets'], extra['fingers'], extra['barre'], family))
    templates = TEMPLATES.get(family)
    if family == 'dim':
        for cand in voicing(root_pc, 'dim7'):    # 감5화음은 dim7 폼으로 근사(7음 추가)
            out.append(dict(cand, approximate=True))
        templates = None
    if templates:
        for tpl in templates:
            f = (root_pc - OPEN_PC[6 - tpl['string']]) % 12
            if f == 0 and tpl.get('open_fingers'):
                frets = [(-1 if d == -9 else d) for d in tpl['deltas']]
                ok, _ = _check(frets, family, root_pc)
                if ok:
                    out.append(_mk(tpl['name'], frets, tpl['open_fingers'], None, family))
            for base in ([f] if f >= 1 else [f + 12]):
                if base < 1 or base > 9:
                    continue
                frets = [(-1 if d == -9 else base + d) for d in tpl['deltas']]
                if min([x for x in frets if x >= 0]) < 0:
                    continue
                fingers = list(tpl['fingers'])
                barre = None
                if tpl['barre'] and f >= 1:
                    off, a, b = tpl['barre']
                    barre = {'fret': base + off, 'from': a, 'to': b, 'finger': 1}
                ok, _ = _check(frets, family, root_pc)
                if ok:
                    out.append(_mk(tpl['name'], frets, fingers, barre, family))
    if family == 'aug':
        out.extend(_aug_voicings(root_pc))
    if family in ('sus4', 'sus2', 'add9', '7sus4', '9'):
        for cand in voicing(root_pc, 'maj'):     # 3화음으로 근사(화면에 근사 표시)
            out.append(dict(cand, approximate=True))
    uniq, seen = [], set()
    for v in out:
        key = tuple(-2 if f is None else f for f in v['frets'])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(v)
    uniq.sort(key=lambda v: (v['difficulty'], v['max_fret']))
    return uniq


def _mk(name, frets, fingers, barre, family):
    played = [f for f in frets if f is not None and f >= 0]
    max_fret = max(played) if played else 0
    base = 1
    if max_fret > 4:
        base = max(1, min([f for f in played if f > 0] or [1]))
    diff = 0
    if barre:
        span = barre['from'] - barre['to'] + 1
        diff = 3 if span >= 4 else 2
        if barre['fret'] >= 5:
            diff += 1
    elif max_fret > 4:
        diff = 3
    if family in SPECIAL:
        diff = min(4, diff + 1)
    return {'shape': name, 'frets': list(frets), 'fingers': list(fingers), 'barre': barre,
            'base': base, 'max_fret': max_fret, 'difficulty': diff}


def _aug_voicings(root_pc):
    out = []
    n = root_pc % 4
    f = 3 + n                      # A폼 증5화음: x (3+n) (2+n) (1+n) (1+n) n — Caug x32110
    if f <= 9:
        frets = [-1, f, f - 1, f - 2, f - 2, f - 3]
        ok, _ = _check(frets, 'aug', root_pc)
        if ok:
            out.append(_mk('aug폼', frets, [0, 3, 2, 1, 1, 0],
                           {'fret': f - 2, 'from': 3, 'to': 2, 'finger': 1}, 'aug'))
    m = (root_pc - OPEN_PC[2]) % 12 or 12   # 4현 증5화음: xx m (m-1) (m-1) (m-2) — Faug xx3221
    if 1 <= m <= 10:
        frets = [-1, -1, m, m - 1, m - 1, m - 2]
        ok, _ = _check(frets, 'aug', root_pc)
        if ok:
            if m - 1 <= 0:
                fingers = [0, 0, 2, 0, 0, 0] if m == 1 else [0, 0, 0, 0, 0, 0]
                barre = None
            elif m - 1 == 1 and m - 2 == 0:
                fingers = [0, 0, 2, 1, 1, 0]
                barre = {'fret': 1, 'from': 3, 'to': 2, 'finger': 1}
            else:
                fingers = [0, 0, 3, 2, 4, 1]
                barre = None
            out.append(_mk('aug4현', frets, fingers, barre, 'aug'))
    return out


def fingering_text(v):
    """'x13331 · 1:5~1번줄 1프렛 바레 2:4번줄3프렛 …' 형태의 한 줄 요약."""
    code = ''.join('x' if (f is None or f < 0) else str(f) for f in v['frets'])
    notes = []
    b = v.get('barre')
    if b:
        notes.append(f"1:{b['from']}~{b['to']}번줄 {b['fret']}프렛 바레")
    for s, fr, fg in zip(range(6, 0, -1), v['frets'], v['fingers']):
        if fr is None or fr < 0:
            continue
        if b and fg == 1 and b['from'] >= s >= b['to'] and fr == b['fret']:
            continue
        if fr == 0:
            notes.append(f'{s}번줄 O')
        else:
            notes.append(f'{fg}:{s}번줄{fr}프렛')
    return code + (' · ' + ' '.join(notes) if notes else '')


def describe(chord_name, capo):
    """실제 울리는 코드 + 카포 → 화면에 쓸 운지 정보.

    카포가 있으면 손 모양은 '실제 코드 - 카포'로 계산한다(에어로밴드 버튼과 같은 기준).
    """
    p = parse(chord_name)
    prefer_flat = 'b' in chord_name or chord_name in ('F',)
    shape_pc = (p['root_pc'] - capo) % 12
    shape = shape_name(shape_pc, p['family'], prefer_flat)
    cands = voicing(shape_pc, p['family'])
    exact = [c for c in cands if not c.get('approximate')]
    if not exact:
        triad = 'min' if p['family'] in ('min', 'm7', 'm6') else 'maj'
        for c in voicing(shape_pc, triad):
            cands.append(dict(c, approximate=True, shape=c['shape'] + ' 근사'))
    best = (exact or cands or [None])[0]
    info = {
        'sounding': chord_name, 'shape': shape, 'capo': capo,
        'family': p['family'], 'bass': p['bass'],
        'shapePc': shape_pc,
    }
    if best:
        info.update({
            'frets': best['frets'], 'fingers': best['fingers'], 'barre': best['barre'],
            'base': best['base'], 'form': best['shape'], 'difficulty': best['difficulty'],
            'fingering': fingering_text(best),
            'approximate': bool(best.get('approximate')),
            'maxFret': best['max_fret'],
        })
        if p['bass']:
            info['bassNote'] = _bass_hint(p['bass'], best)
    else:
        info.update({'frets': [], 'fingers': [], 'barre': None, 'base': 1,
                     'fingering': '', 'difficulty': 4, 'approximate': True, 'maxFret': 0})
    return info


def _bass_hint(bass, v):
    """슬래시 코드 베이스 안내 — 운지에 베이스를 끼워 넣지 않고, 반주가 잡아 준다는 사실을 적는다."""
    return f'슬래시 코드: 베이스는 {bass}. 기타에서는 이 코드만 쳐도 반주와 맞습니다.'


if __name__ == '__main__':
    tests = ['Bb', 'B', 'C#', 'Eb', 'F#', 'Ab', 'Bbm', 'C#m', 'Ebm', 'F#m', 'G#m', 'Abm',
             'B7', 'Bb7', 'C#7', 'Faug', 'Abaug', 'F#m7b5', 'Bbm7b5', 'AbM7', 'EbM7',
             'Am6', 'Bdim7', 'F', 'C', 'G', 'D', 'A', 'E', 'Am', 'Dm', 'Em', 'Bm', 'Cm',
             'Eb/G', 'Bb/C', 'Cdim', 'Bbsus4']
    for t in tests:
        for capo in (0, 2):
            d = describe(t, capo)
            print(f"{t:8s} capo{capo} → {d['shape']:8s} {d['fingering'][:70]:70s} 난이도 {d['difficulty']}"
                  f"{' 근사' if d.get('approximate') else ''}")
