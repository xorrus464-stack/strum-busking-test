#!/usr/bin/env python3
"""코드스코어 공개 미리보기(4행 = 16마디)에서 연습용 4박 마디 카드를 자동 생성한다.

각 행(musics[].sort)은 16분 슬롯 16칸 = 4마디(4/4 기준)이며, 1·5·9·13칸이 각 마디 1박이다.
- 입력: tmp/score/<slug>.json
- 출력: tools/auto_charts.json (검수 전 초안)
"""
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parents[1]
SCORE = BASE / 'tmp' / 'score'
FLAT = str.maketrans({'ᵇ': 'b', '♭': 'b', '♯': '#', '＃': '#', '⁄': '/'})


def clean_chord(txt):
    if not txt:
        return ''
    t = re.sub(r'<[^>]+>', '', txt).translate(FLAT).replace(' ', '').strip()
    if t in ('(N.C)', 'N.C', '(N.C.)', '(N,C)', ''):
        return ''
    m = re.match(r'^([A-G][#b]?)(.*)$', t)
    if not m:
        return ''
    root, rest = m.group(1), m.group(2)
    # 소문자 m 으로 시작하면 단3화음, 대문자 M(예: CM7)은 장3화음
    quality = 'm' if (rest.startswith('m') and not rest.startswith('maj')) else ''
    return root + quality


def row_bars(slots):
    """16칸 → 4마디. 각 마디는 최대 2개 코드(1박·3박)로 정리."""
    out = []
    for start in (1, 5, 9, 13):
        beats = [clean_chord(slots[i - 1]) for i in range(start, start + 4)]
        if not any(beats):
            continue
        bar = []
        last = ''
        for i, c in enumerate(beats):
            c = c or last
            last = c
            if c and (not bar or bar[-1] != c):
                bar.append(c)
        if len(bar) > 2:
            bar = [bar[0], bar[-1]]
        if bar:
            out.append(bar)
    return out


def main():
    draft = {}
    for f in sorted(SCORE.glob('*.json')):
        rec = json.loads(f.read_text(encoding='utf-8'))
        info = rec.get('info') or {}
        rows = rec.get('bars') or []
        if not info or not info.get('original_key') or not rows:
            continue
        bars = []
        ts = (info.get('beat') or '4/4').replace(' ', '')
        if ts.startswith('6/8') or ts.startswith('3/4'):
            # 6/8·3/4 은 한 마디의 박 수가 달라 4박 그리드로 나누지 않고, 코드 변화 순서를 2개씩 묶는다
            seen = []
            for b in rows[:4]:
                for c in [clean_chord(x) for x in b['slots']]:
                    if c and (not seen or seen[-1] != c):
                        seen.append(c)
            bars = [[seen[i], seen[i + 1]] if i + 1 < len(seen) else [seen[i]] for i in range(0, len(seen), 2)]
            bars = bars[:8]
        else:
            for b in rows[:4]:
                bars.extend(row_bars(b['slots']))
        if len(bars) < 2:
            continue
        rows4 = [bars[i:i + 4] for i in range(0, len(bars), 4)]
        sections = [{'name': f'{"ABCD"[i]} · {i*4+1}–{i*4+len(ch)}마디', 'bars': ch} for i, ch in enumerate(rows4)]
        draft[rec['work']['slug']] = {
            'title': re.sub(r'<[^>]+>', '', info.get('title') or ''),
            'singer': info.get('singer'),
            'originalKey': (info.get('original_key') or '').translate(FLAT).split('-')[0].strip(),
            'timeSignature': info.get('beat'),
            'bpm': int(float(info.get('tempo'))) if info.get('tempo') else None,
            'sections': sections,
            'scoreId': info.get('id'),
        }
    (BASE / 'tools' / 'auto_charts.json').write_text(json.dumps(draft, ensure_ascii=False, indent=1), encoding='utf-8')
    for slug, d in draft.items():
        print(f"{slug}: {d['title']} / {d['singer']} | {d['originalKey']} {d['timeSignature']} {d['bpm']}")
        for s in d['sections']:
            print('   ', s['name'], ' | '.join(' '.join(b) for b in s['bars']))


if __name__ == '__main__':
    main()
