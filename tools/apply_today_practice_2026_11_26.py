#!/usr/bin/env python3
"""'오늘의 연습' 개편(2026-11-26) 반영 — 주간 연습 Day 별 실제 코드 3개를 seed.js 에 넣고 버전을 올린다.

- data/week-plan.json 이 원본이다(각 Day 의 chords/chordsNote 추가분 포함).
- src/app.js 의 CHORD_SHAPES 에 있는 코드만 Day 코드로 쓸 수 있는지 확인한다.
- seed.js 끝의 lessons/weekPlan 블록을 다시 쓰고, meta.seedVersion 26 → 27.
- index.html 의 ?v=27 → ?v=28, sw.js 의 캐시 이름 v27 → v28 도 함께 올린다.

실행: python3 tools/apply_today_practice_2026_11_26.py
"""
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parents[1]
MARK = '\n/* 주간 연습 · 오른손 주법 강좌 (2026-11-26) */\n'
NEXT_SEED = 27
NEXT_CACHE = 28

lessons = json.loads((BASE / 'data' / 'lessons.json').read_text(encoding='utf-8'))
week = json.loads((BASE / 'data' / 'week-plan.json').read_text(encoding='utf-8'))
app_js = (BASE / 'src' / 'app.js').read_text(encoding='utf-8')

shapes = set(re.findall(r"^    ([A-G][#b]?\w*):\{form:", app_js, re.M))
assert len(shapes) >= 15, shapes
assert len(week['days']) == 7, len(week['days'])
lesson_keys = {l['key'] for l in lessons['lessons']}
used = set()
for d in week['days']:
    assert d.get('chords') and 2 <= len(d['chords']) <= 3, (d['day'], d.get('chords'))
    for c in d['chords']:
        assert c in shapes, (d['day'], c)
        used.add(c)
    for k in d['lessons']:
        assert k in lesson_keys, (d['day'], k)
print('day chords', sorted(used))

seed_path = BASE / 'src' / 'seed.js'
text = seed_path.read_text(encoding='utf-8')
if MARK in text:
    text = text[:text.index(MARK)]
text = text.rstrip('\n')
text = re.sub(r'"seedVersion":\d+', f'"seedVersion":{NEXT_SEED}', text, count=1)
assert f'"seedVersion":{NEXT_SEED}' in text

block = (
    MARK
    + 'window.STRUM_SEED.lessons = '
    + json.dumps(lessons, ensure_ascii=False, separators=(',', ':'))
    + ';\nwindow.STRUM_SEED.weekPlan = '
    + json.dumps(week, ensure_ascii=False, separators=(',', ':'))
    + ';\n'
)
seed_path.write_text(text + block, encoding='utf-8')

meta_path = BASE / 'data' / 'metadata.json'
meta = json.loads(meta_path.read_text(encoding='utf-8'))
meta['seedVersion'] = NEXT_SEED
meta['weekPlanDays'] = len(week['days'])
meta['todayPracticeVersion'] = '2026-11-26'
meta['todayPracticeNote'] = (
    "홈·상단 메뉴의 '오늘의 연습'이 모바일에서 눌리지 않던 원인은 히어로 배경 장식(.hero:after)이 "
    "버튼 위를 덮고 있었기 때문입니다. 장식에 pointer-events:none 을 주고, 모바일 상단 메뉴에서 "
    "'오늘의 연습'을 맨 앞으로 옮겼습니다. 오늘의 연습 화면은 주간 연습의 해당 Day(미시작이면 Day 1)와 "
    "목표곡을 묶어 '오늘 할 일 3가지'(① 목표곡 악보·MR 80%, ② 오른손 주법 영상, ③ 실제 코드 2~3개 운지표 20%)를 "
    "맨 위에 두고, 5단계 루틴 각 줄에 관련 기능 버튼을 붙였습니다."
)
meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

idx = BASE / 'index.html'
h = idx.read_text(encoding='utf-8')
h = re.sub(r'\?v=\d+', f'?v={NEXT_CACHE}', h)
idx.write_text(h, encoding='utf-8')

sw = BASE / 'sw.js'
s = sw.read_text(encoding='utf-8')
s = re.sub(r"strum-busking-test-v\d+", f'strum-busking-test-v{NEXT_CACHE}', s, count=1)
sw.write_text(s, encoding='utf-8')

print('seedVersion', NEXT_SEED, 'cache v', NEXT_CACHE, 'seed.js bytes', seed_path.stat().st_size)
