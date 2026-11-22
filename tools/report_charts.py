#!/usr/bin/env python3
"""악보 데이터(남자키·카포·박자·BPM·슬롯·근거)를 사람이 읽는 문서로 출력한다.

실행: python3 tools/report_charts.py  → docs/악보_데이터_2026-11-22.md
"""
import json
import pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
songs = json.loads((BASE / 'data' / 'songs.seed.json').read_text(encoding='utf-8'))
meta = json.loads((BASE / 'data' / 'metadata.json').read_text(encoding='utf-8'))

ready = [s for s in songs if s.get('chartStatus') == 'ready']
partial = [s for s in songs if s.get('chartStatus') == 'partial']
entry = [s for s in songs if s['id'].startswith(('verified-', 'restored-')) or s['verification'] in ('added-by-user', 'imported')]
pending = [s for s in entry if s.get('chartStatus') not in ('ready', 'partial')]

lines = ['# 악보 데이터 — 남자키 · AeroBand Capo · 박자 · BPM · 원터치 매핑', '',
         f'기준: {meta.get("chartVersion")} · seedVersion {meta.get("seedVersion")}', '',
         f'- 악보 준비 완료 **{len(ready)}곡**', f'- 부분 확인 **{len(partial)}곡** (키/박자/BPM만 확정)',
         f'- 코드 검수 대기 **{len(pending)}곡**', '',
         '남자키는 원곡 보컬 성별에 따라 −2~−4반음을 기준으로 잡고, 원터치 10버튼(C·Dm·Em·F·G / Cm·D·E·Fm·Gm)에 가장 많이 들어가는 카포를 골랐습니다.',
         '마디 배치는 확인한 코드표의 순서를 4박 마디 카드로 정리한 **연습용 배치**이며, 원곡의 세부 마디 배치와 다를 수 있습니다.', '',
         '## 준비 완료', '',
         '| 곡 | 가수 | 원키 | 남자키 | Capo | 폼 | 박자 | BPM | 원터치 | 슬롯 | 단계 |',
         '|---|---|---|---|---|---|---|---|---|---|---|']
for s in sorted(ready, key=lambda x: (x['chart']['stage'], x['title'])):
    c = s['chart']
    lines.append(f"| {s['title']} | {s['artist']} | {c['originalKey']} | {c['maleKey']} | +{c['capo']} | {c['formText']} | "
                 f"{c['timeSignature']} | {c['bpm']} | {c['coverage']['mapped']}/{c['coverage']['total']} | {len(c['slots'])} | {c['stage']} |")
lines += ['', '## 곡별 근거', '']
for s in sorted(ready, key=lambda x: (x['chart']['stage'], x['title'])):
    c = s['chart']
    lines.append(f"### {s['title']} — {s['artist']}")
    lines.append(f"- 원키 {c['originalKey']} → 남자키 **{c['maleKey']}** (−{c['maleShift']}반음) · AeroBand **Capo +{c['capo']}** ({c['formText']})")
    lines.append(f"- 박자 {c['timeSignature']} ({c['timeNote'] or '출처 표기'}) · BPM {c['bpm']} ({c['bpmNote'] or '-'})")
    if c['slots']:
        lines.append('- SimplifyChord: ' + ', '.join(f"S{x['slot']} {x['chord']}" for x in c['slots']))
    lines.append(f"- 오른손: {c['stroke']}")
    if c.get('percussiveReady'):
        lines.append(f"- 퍼커시브: {c['percussive']}")
    for e in c['evidence']:
        lines.append(f"- 근거: [{e['label']}]({e['url']}) — {e['note']}")
    lines.append('')
lines += ['## 부분 확인(키·박자·BPM만)', '', '| 곡 | 가수 | 원키 | 박자 | BPM | 사유 |', '|---|---|---|---|---|---|']
for s in partial:
    c = s['chart']
    lines.append(f"| {s['title']} | {s['artist']} | {c.get('originalKey') or '—'} | {c.get('timeSignature') or '—'} | {c.get('bpm') or '—'} | {s.get('chartNote', '')} |")
lines += ['', '## 코드 검수 대기', '', '| 곡 | 가수 | 원본 번호 | 사유 |', '|---|---|---|---|']
for s in pending:
    lines.append(f"| {s['title']} | {s['artist']} | {', '.join(map(str, s['sourceIndices'])) or '—'} | {s.get('chartNote') or '코드표 미확보'} |")
lines.append('')
(BASE / 'docs' / '악보_데이터_2026-11-22.md').write_text('\n'.join(lines), encoding='utf-8')
print('written', len(ready), len(partial), len(pending))
