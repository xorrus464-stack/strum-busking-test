#!/usr/bin/env python3
"""주간 연습(Day 1~7) 플랜과 오른손 주법 강좌를 seed.js 에 넣고 시드 버전을 올린다.

- data/week-plan.json, data/lessons.json 이 원본이다.
- seed.js 끝에 STRUM_SEED.lessons / STRUM_SEED.weekPlan 을 덧붙인다(앱은 이 값을 읽는다).
- meta.seedVersion 25 → 26, data/metadata.json 도 같이 맞춘다.

실행: python3 tools/apply_week_lessons_2026_11_26.py
"""
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parents[1]
MARK = '\n/* 주간 연습 · 오른손 주법 강좌 (2026-11-26) */\n'

lessons = json.loads((BASE / 'data' / 'lessons.json').read_text(encoding='utf-8'))
week = json.loads((BASE / 'data' / 'week-plan.json').read_text(encoding='utf-8'))

assert len(lessons['lessons']) == 9, len(lessons['lessons'])
assert len(week['days']) == 7, len(week['days'])
for lesson in lessons['lessons']:
    vid = lesson['video']['id']
    assert re.fullmatch(r'[A-Za-z0-9_-]{11}', vid), vid
    if lesson.get('alt'):
        assert re.fullmatch(r'[A-Za-z0-9_-]{11}', lesson['alt']['id']), lesson['alt']['id']
keys = {l['key'] for l in lessons['lessons']}
for day in week['days']:
    for k in day['lessons']:
        assert k in keys, (day['day'], k)
seen = set()
for day in week['days']:
    seen.update(day['lessons'])
assert seen == keys, sorted(keys - seen)

seed_path = BASE / 'src' / 'seed.js'
text = seed_path.read_text(encoding='utf-8')
if MARK in text:
    text = text[:text.index(MARK)]
text = text.rstrip('\n')

# 이미 26 이면 그대로 둔다(재실행해도 안전)
if '"seedVersion":25' in text:
    text = text.replace('"seedVersion":25', '"seedVersion":26', 1)
assert '"seedVersion":26' in text

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
meta['seedVersion'] = 26
meta['lessonVersion'] = lessons['version']
meta['lessonNote'] = (
    '2026-11-26 주간 연습(Day 1~7)과 오른손 주법 강좌 9개를 추가했습니다. 강좌 영상은 '
    'YouTube oEmbed HTTP 200으로 제목·채널을 확인한 실제 레슨 영상이고, 커버·연주 영상은 넣지 않았습니다. '
    '라이브 사이트에서 대표 영상 5개(채널별 1개)를 미니 플레이어로 직접 재생해 임베드 재생까지 확인했고, 모든 카드에 YouTube 직접 열기 링크도 함께 둡니다.'
)
meta['weekPlanDays'] = len(week['days'])
meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print('seedVersion', meta['seedVersion'], 'lessons', len(lessons['lessons']), 'days', len(week['days']))
print('seed.js bytes', seed_path.stat().st_size)
