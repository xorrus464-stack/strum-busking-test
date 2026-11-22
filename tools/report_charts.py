#!/usr/bin/env python3
"""악보 데이터(남자키·카포·박자·BPM·슬롯·근거)와 재생목록 분류를 사람이 읽는 문서·CSV로 출력한다.

실행: python3 tools/report_charts.py
출력: docs/악보_데이터_2026-11-22.md, docs/재생목록_분류_2026-11-22.md, data/playlist-classification.csv
"""
import csv
import json
import pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
songs = json.loads((BASE / 'data' / 'songs.seed.json').read_text(encoding='utf-8'))
meta = json.loads((BASE / 'data' / 'metadata.json').read_text(encoding='utf-8'))

ready = [s for s in songs if s.get('chartStatus') == 'ready']
partial = [s for s in songs if s.get('chartStatus') == 'partial']
pending = [s for s in songs if s.get('chartStatus') == 'pending']
refs = [s for s in songs if s.get('category') == 'reference']
orig = [s for s in songs if s.get('category') == 'original']
play = [s for s in songs if s['id'].startswith('playlist-')]

# 곡(원곡) 단위로 묶어 서로 다른 곡 수를 센다
by_work = {}
for s in ready + partial:
    by_work.setdefault(s.get('workTitle') or s['title'], []).append(s)


def title_of(s):
    return s.get('workTitle') or s['title']


def artist_of(s):
    return s.get('workArtist') or s['artist']


lines = ['# 악보 데이터 — 남자키 · AeroBand Capo · 박자 · BPM · 원터치 매핑', '',
         f'기준: {meta.get("chartVersion")} · seedVersion {meta.get("seedVersion")}', '',
         f'- 악보 완료 **{len(ready)}개 항목** (서로 다른 곡 **{meta["uniqueChartSongCount"]}곡**)',
         f'- 부분 확인 **{len(partial)}개** (키/박자/BPM만 확정)',
         f'- 코드 검수 대기 **{len(pending)}개**',
         f'- 비음악·참고 영상 **{len(refs)}개**', f'- 자작곡 **{len(orig)}개**', '',
         '남자키는 **여성 원곡 −5반음, 남성 원곡 −2반음**을 기본으로 잡고, AeroBand 원터치 10버튼(C·Dm·Em·F·G / Cm·D·E·Fm·Gm)에 가장 많이 들어가는 카포를 골랐습니다.',
         '마디 배치는 확인한 코드표(주로 코드스코어 공개 미리보기)의 순서를 4박 마디 카드로 정리한 **연습용 배치**이며, 원곡의 세부 마디와 다를 수 있습니다.',
         '같은 곡의 커버 영상은 같은 악보를 연결했습니다(항목 수와 서로 다른 곡 수가 다릅니다).', '',
         '## 악보 완료', '',
         '| 곡 | 가수 | 원키 | 남자키 | Capo | 폼 | 박자 | BPM | 원터치 | 슬롯 | 단계 |', '|---|---|---|---|---|---|---|---|---|---|---|']
for s in sorted(ready, key=lambda x: (x['chart']['stage'], title_of(x))):
    c = s['chart']
    lines.append(f"| {title_of(s)} | {artist_of(s)} | {c['originalKey']} | {c['maleKey']} | +{c['capo']} | {c['formText']} | "
                 f"{c['timeSignature']} | {c['bpm']} | {c['coverage']['mapped']}/{c['coverage']['total']} | {len(c['slots'])} | {c['stage']} |")
lines += ['', '## 곡별 근거', '']
seen = set()
for s in sorted(ready, key=lambda x: (x['chart']['stage'], title_of(x))):
    key = title_of(s)
    if key in seen:
        continue
    seen.add(key)
    c = s['chart']
    lines.append(f'### {key} — {artist_of(s)}')
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
    lines.append(f"| {title_of(s)} | {artist_of(s)} | {c.get('originalKey') or '—'} | {c.get('timeSignature') or '—'} | {c.get('bpm') or '—'} | {s.get('chartNote', '')} |")
lines += ['', '## 코드 검수 대기(곡은 확인, 악보 미확보)', '', '| 곡 | 가수 | 원본 번호 | 사유 |', '|---|---|---|---|']
for s in pending:
    lines.append(f"| {title_of(s)} | {artist_of(s)} | {', '.join(map(str, s['sourceIndices'])) or '—'} | {s.get('categoryNote') or s.get('chartNote') or '코드표 미확보'} |")
lines.append('')
(BASE / 'docs' / '악보_데이터_2026-11-22.md').write_text('\n'.join(lines), encoding='utf-8')

# 재생목록 분류 문서
pl = ['# 공개 재생목록 155개 항목 분류 (2026-11-22)', '',
      f'- 악보 완료 {len([s for s in play if s.get("category") == "chart"])}개 · 부분 확인 {len([s for s in play if s.get("category") == "partial"])}개 · '
      f'검수 대기 {len([s for s in play if s.get("category") == "pending"])}개 · 비음악·참고 {len([s for s in play if s.get("category") == "reference"])}개 · 자작곡 {len([s for s in play if s.get("category") == "original"])}개',
      '', '## 악보 완료(또는 같은 곡 악보 연결)', '', '| 원본 # | 영상 제목 | 확인한 곡 | 가수 | 남자키 | Capo | 박자 | BPM |', '|---|---|---|---|---|---|---|---|']
for s in sorted([s for s in play if s.get('category') in ('chart', 'partial')], key=lambda x: x['sourceIndices'][0]):
    c = s['chart']
    pl.append(f"| {s['sourceIndices'][0]} | {s['title'][:52]} | {title_of(s)} | {artist_of(s)} | {c['maleKey']} | +{c['capo']} | {c['timeSignature']} | {c['bpm']} |")
pl += ['', '## 검수 대기(곡명은 확인, 인터넷 악보 미확보)', '', '| 원본 # | 영상 제목 | 곡 | 가수 | 사유 |', '|---|---|---|---|---|']
for s in sorted([s for s in play if s.get('category') == 'pending'], key=lambda x: x['sourceIndices'][0]):
    pl.append(f"| {s['sourceIndices'][0]} | {s['title'][:52]} | {title_of(s)} | {artist_of(s)} | {s.get('categoryNote') or '코드표 미확보'} |")
pl += ['', '## 비음악·참고 영상(악보 대상 아님)', '', '| 원본 # | 영상 제목 | 채널 | 사유 |', '|---|---|---|---|']
for s in sorted(refs, key=lambda x: (x['sourceIndices'] or [0])[0]):
    pl.append(f"| {s['sourceIndices'][0] if s['sourceIndices'] else '—'} | {s['title'][:52]} | {s['artist']} | {s.get('categoryNote', '')} |")
pl += ['', '## 자작곡(채보 필요)', '', '| 원본 # | 영상 제목 | 사유 |', '|---|---|---|']
for s in orig:
    pl.append(f"| {s['sourceIndices'][0] if s['sourceIndices'] else '—'} | {s['title'][:52]} | {s.get('categoryNote', '')} |")
pl.append('')
(BASE / 'docs' / '재생목록_분류_2026-11-22.md').write_text('\n'.join(pl), encoding='utf-8')

with (BASE / 'data' / 'playlist-classification.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['원본번호', 'id', '영상제목', '분류', '곡명', '가수', '남자키', '원키', 'Capo', '박자', 'BPM', '사유/메모'])
    for s in sorted(songs, key=lambda x: (x['id'])):
        w.writerow([','.join(map(str, s['sourceIndices'])), s['id'], s['title'], s.get('category', ''),
                    title_of(s), artist_of(s), s.get('maleKey', ''), s.get('key', ''),
                    (s.get('chart') or {}).get('capo', ''), (s.get('chart') or {}).get('timeSignature', ''),
                    (s.get('chart') or {}).get('bpm', ''), s.get('categoryNote') or s.get('chartNote', '')])

print('written', len(ready), len(partial), len(pending), len(refs), len(orig))
