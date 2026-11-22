#!/usr/bin/env python3
"""4곡 순수 MR 재검수 결과를 곡 데이터에 반영한다 (seed v18, 2026-11-23).

1) MR 음원 2건 연결
   verified-017 「나는 버려질 장난감」   → media/toy-mr.mp3      (AI 보컬 제거 UVR Online MDX VocFT)
   verified-021 「날씨가 좋고 바람도 좋아」 → media/weather-mr.mp3  (같은 방식)
2) verified-017: 4:01 전체 MR 기준
   - 마디 7·10·26: 악보에 적힌 F/Ab7을 MR 실측(F·B♭m)에 맞춰 수정
   - 마디 24·36: 악보 Db → MR 실측 G♭
   - 3:00에서 끝나던 악보에 3:00~4:02 마지막 반복 13마디 추가 (36 → 49마디)
3) playlist-072 「커피」: BPM 99 → 98 (MR 실측 ♩98.00)
4) playlist-173 「괜히 보고 싶은 사실…」: BPM 76 → 74 (MR 실측 ♩74.1)
   + 구간 시각을 새 BPM에 맞춰 다시 계산(구간 이름의 성질 표기는 유지)
5) metadata.json: seedVersion 18 · mrLinkCount 162 · mrWorkCount 135 · mrDisclosure 갱신
6) src/seed.js 재작성, index.html·app.js·styles.css ?v=18

실행: python3 tools/apply_mr_recheck_2026_11_23_v18.py
"""
import json
import pathlib
import re
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'tools'))
from build_charts import build_chart  # noqa: E402

SEED_VERSION = 18
DATE = '2026-11-23'

LOCAL_MR = [
    {
        'id': 'verified-017',
        'file': 'media/toy-mr.mp3',
        'mrTitle': '아소 · 아날로그소년 - 나는 버려질 장난감 (AI 보컬 제거 반주)',
        'mrNote': 'AI 보컬 제거(UVR Online MDX VocFT) 추출 반주 MP3 · 2026-11-23',
        'minSize': 3_600_000,
        'duration': (241.0, 242.5),
    },
    {
        'id': 'verified-021',
        'file': 'media/weather-mr.mp3',
        'mrTitle': '날씨가 좋고 바람도 좋아 (AI 보컬 제거 반주)',
        'mrNote': 'AI 보컬 제거(UVR Online MDX VocFT) 추출 반주 MP3 · 2026-11-23',
        'minSize': 2_800_000,
        'duration': (188.0, 190.0),
    },
]

# verified-017: 바뀌는 마디 (1부터) — MR 실측 근음과 악보가 어긋난 곳
TOY_BAR_FIXES = {
    7: ['F', 'Bbm'],     # 기존 F/Db → MR: F(2박)→B♭m(2박), 저역 B♭ 0.62
    10: ['F'],           # 기존 Ab7   → MR: F(♩F단음) 저역 F 0.61
    24: ['Gb'],          # 기존 Db    → MR: G♭ 저역 G♭ 0.47
    26: ['F', 'Bbm'],    # 기존 Ab7/Bbm → MR: F(2박)→B♭m(2박)
    36: ['Gb'],          # 기존 Db    → MR: G♭ 저역 G♭ 0.55
}
TOY_TAIL = {
    'name': '마지막 반복 (3:00–4:02) · 순수 MR',
    'bars': [['Gb'], ['Db'], ['F'], ['Bbm']] * 3 + [['Gb']],
}


def ffprobe_duration(path):
    out = subprocess.run([str(BASE.parent / 'ffmpeg'), '-hide_banner', '-i', str(path)],
                         capture_output=True, text=True).stderr
    m = re.search(r'Duration: (\d+):(\d\d):(\d\d\.\d+)', out)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def mmss(sec):
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def retime_sections(sections, bpm, first_bar_start):
    """구간 이름의 시각(0:04–0:42)을 새 BPM·마디 길이로 다시 쓴다. 성질 표기는 유지."""
    bar = 4 * 60 / bpm
    t = first_bar_start
    for sec in sections:
        n = len(sec['bars'])
        start, end = t, t + n * bar
        t = end
        tail = ''
        m = re.search(r'(\d+:\d\d)\s*–\s*(\d+:\d\d)(.*)$', sec['name'])
        if m:
            tail = m.group(3)
            sec['name'] = f"{re.sub(r'\s*\d+:\d\d\s*–\s*\d+:\d\d.*$', '', sec['name'])} {mmss(start)}–{mmss(end)}{tail}"
        else:
            sec['name'] = f"{sec['name']} {mmss(start)}–{mmss(end)}"
    return sections


def main():
    seed_path = BASE / 'data' / 'songs.seed.json'
    meta_path = BASE / 'data' / 'metadata.json'
    songs = json.loads(seed_path.read_text(encoding='utf-8'))
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    by_id = {s['id']: s for s in songs}

    # 1) MR 음원 연결
    for item in LOCAL_MR:
        mp3 = BASE / item['file']
        assert mp3.exists() and mp3.stat().st_size >= item['minSize'], (item['file'], 'MR 음원 없음/작음')
        dur = ffprobe_duration(mp3)
        assert dur and item['duration'][0] <= dur <= item['duration'][1], (item['file'], dur, '길이 불일치')
        s = by_id[item['id']]
        s['mrAudioUrl'] = item['file']
        s['mrTitle'] = item['mrTitle']
        s['mrNote'] = item['mrNote']
        s['mrSource'] = 'user-recording'
        s.pop('mrUrl', None)
        print(f"MR {item['id']}: {item['file']} ({mp3.stat().st_size // 1024}KB, {dur:.2f}s)")

    # 2) verified-017 — 마디 수정 + 마지막 반복 추가
    toy = by_id['verified-017']
    chart = toy['chart']
    old_bars = [bar for sec in chart['sections'] for bar in sec['bars']]
    assert len(old_bars) == 36, len(old_bars)
    fixed = []
    for i, bar in enumerate(old_bars, 1):
        names = TOY_BAR_FIXES.get(i) or [c['orig'] for c in bar]
        fixed.append(names)
    # 기존 구간 경계 유지 + 새 구간 추가
    sections = []
    k = 0
    for sec in chart['sections']:
        n = len(sec['bars'])
        sections.append({'name': sec['name'], 'bars': fixed[k:k + n]})
        k += n
    sections.append({'name': TOY_TAIL['name'], 'bars': TOY_TAIL['bars']})
    assert sum(len(x['bars']) for x in sections) == 49

    data = {
        'originalKey': chart['originalKey'],
        'timeSignature': chart['timeSignature'],
        'bpm': chart['bpm'],
        'capo': chart['capo'],
        'stage': chart['stage'],
        'stroke': chart['stroke'],
        'percussive': chart['percussive'],
        'why': chart['why'],
        'sections': sections,
    }
    new_chart, _male = build_chart('verified-017', data)
    assert new_chart['capo'] == chart['capo'], (new_chart['capo'], chart['capo'])
    assert new_chart['originalKey'] == chart['originalKey'] and new_chart['maleKey'] == chart['maleKey']
    assert new_chart['formText'] == chart['formText'], (new_chart['formText'], chart['formText'])
    chart['sections'] = new_chart['sections']
    chart['slots'] = new_chart['slots']
    chart['coverage'] = new_chart['coverage']
    chart['bpmNote'] = '순수 MR 실측 ♩48.66 (격자 탐색 0.02BPM · 30초 창 자기상관 48.65~48.73)'
    chart['timeNote'] = '순수 MR 실측 — ♩48.66 · 4/4 · 한 마디 4.93초 · 3잇단 8분(12/8) 계열'
    chart['note'] = (
        '순수 MR(보컬 제거) 재검수 2026-11-23 — AI 보컬 제거(UVR Online MDX VocFT)로 뽑은 반주 '
        '4:01.74 전체에서 CQT 크로마·저역 근음(45~200Hz)·온셋 템포를 다시 뽑았습니다. '
        '실측 ♩48.66·4/4·한 마디 4.93초로 기존 49·4/4와 같고, 조성도 전체 크로마 D♭장조 0.968'
        '(나란한 B♭단조 0.982)로 원키 D♭을 유지합니다. '
        '마디 36개를 1:1 대조해 근음 일치 28/36(구간 시각 기준)을 확인했고, 어긋난 마디 7·10·26의 '
        'F·A♭7 표기를 MR 실측(F·B♭m)으로, 마디 24·36의 D♭을 G♭으로 고쳤습니다. '
        '기존 악보가 3:00에서 끝나던 부분은 MR 전체 길이에 맞춰 3:00~4:02 마지막 반복 13마디를 더해 '
        '49마디로 늘렸습니다. MR에서는 코드가 2박마다 바뀌는 마디가 많아(마디 안 두 코드) '
        '마디 안 패스 코드와 7th·sus 성질은 아직 청음 확인이 필요합니다.'
    )
    chart['basis'] = (
        (chart.get('basis') or '').split(' 2026-11-23')[0].strip()
        + ' 2026-11-23 순수 MR 재검수: 반주 4:01.74에서 4.93초 마디 격자로 마디별 크로마·저역 근음을 '
          '다시 뽑아 36마디를 대조했고(근음 일치 28/36), 마디 7·10·24·26·36을 MR 값으로 고친 뒤 '
          '3:00~4:02 마지막 반복 13마디를 추가했습니다. 마디 안 패스 코드와 7th·sus 성질은 청음 확인이 필요합니다.'
    )
    chart['evidence'].append({
        'label': '순수 MR(보컬 제거) 실측 — media/toy-mr.mp3',
        'url': toy['videoUrl'],
        'note': 'AI 보컬 제거(UVR Online MDX VocFT) 반주 4:01.74 · CQT 크로마 + 저역 근음(45~200Hz) + '
                '온셋 격자 템포 · ♩48.66 · D♭장조 0.968 · 마디 49개',
    })
    toy['chartNote'] = chart['note']
    toy['bpm'] = chart['bpm']
    toy['strumming'] = chart['stroke']
    toy['chords'] = ' / '.join(' '.join(c['orig'] for c in bar) for sec in chart['sections'] for bar in sec['bars'])
    toy['notes'] = (
        (toy['notes'].split(' 2026-11-23 순수 MR')[0]).strip()
        + ' 2026-11-23 순수 MR 재검수: AI 보컬 제거 반주 4:01.74 전체로 코드·BPM·마디선을 다시 확인하고 '
          '3:00~4:02 마지막 반복 13마디를 추가했습니다.'
    )

    # 3) 커피 — BPM 99 → 98
    coffee = by_id['playlist-072']
    c = coffee['chart']
    c['bpm'] = 98
    coffee['bpm'] = 98
    c['bpmNote'] = '순수 MR 실측 ♩98.00 (격자 탐색 0.02BPM) · 30초 창 자기상관 97.5~97.9'
    c['timeNote'] = '순수 MR 실측 — ♩98.00 · 4/4 · 한 마디 2.45초'
    c['stroke'] = '↓ · ↓↑ · ↓↑ (98bpm 8분, 한 마디 한 코드)'
    coffee['strumming'] = c['stroke']
    retime_sections(c['sections'], 98, 4.0)
    c['note'] = (
        '순수 MR(보컬 제거) 재검수 2026-11-23 — AI 보컬 제거(UVR Online MDX VocFT) 반주 3:02.13에서 '
        'CQT 크로마·저역 근음·온셋 템포를 다시 뽑았습니다. 템포는 ♩98.00으로, 기존 99·99.384 표기를 '
        '정정합니다(30초 창 자기상관도 97.5~97.9로 98 쪽). 마디 길이는 2.45초입니다. '
        '조성은 F단조 0.925 대 D♭장조 0.915로 사실상 동률이라 표기는 D♭(F단조 나란한조)을 유지합니다. '
        'A♭·G♭maj7·B♭m7·Fm 진행도 그대로 확인됐습니다. 다만 MR에서는 코드가 2박마다 바뀌는 지점이 '
        '반복 확인되어(A♭–G♭–Fm–B♭m 계열), 지금의 1마디 1코드 배치는 연습용 근사입니다. '
        '마디 안 패스 코드와 7th·sus 성질은 청음 확인이 필요합니다. '
        '이 곡은 채널 제목과 달리 nanome이 2025-08-04 발표한 곡이며 주성 님 자작곡이 아닙니다.'
    )
    coffee['chartNote'] = c['note']
    c['basis'] = (
        (c.get('basis') or '').split(' 2026-11-23')[0].strip()
        + ' 2026-11-23 순수 MR 재검수: 반주 3:02.13에서 ♩98.00(기존 99.384 표기 정정)과 F단조 0.925/D♭장조 0.915를 '
          '확인했습니다. 코드가 2박마다 바뀌는 지점이 반복되어 1마디 1코드 배치는 연습용 근사로 남깁니다.'
    )
    c['evidence'].append({
        'label': '순수 MR(보컬 제거) 실측 — media/coffee-mr.mp3',
        'url': coffee['videoUrl'],
        'note': 'AI 보컬 제거(UVR Online MDX VocFT) 반주 3:02.13 · ♩98.00 · F단조 0.925 / D♭장조 0.915',
    })
    coffee['notes'] = (
        (coffee['notes'].split(' 2026-11-23 순수 MR')[0]).strip()
        + ' 2026-11-23 순수 MR 재검수: AI 보컬 제거 반주로 템포를 ♩98.00으로 정정하고 키·코드 진행을 다시 확인했습니다.'
    )

    # 4) jehoda — BPM 76 → 74
    jehoda = by_id['playlist-173']
    j = jehoda['chart']
    j['bpm'] = 74
    jehoda['bpm'] = 74
    j['bpmNote'] = '순수 MR 실측 ♩74.1 (구간별 74.0~74.9) · 하프타임 148 · 기존 76 표기 정정'
    j['timeNote'] = '순수 MR 실측 — ♩74.1 · 4/4 · 한 마디 3.24초'
    j['stroke'] = '↓ · ↓↑ · ↓↑ (74bpm, 한 마디 한 코드)'
    jehoda['strumming'] = j['stroke']
    retime_sections(j['sections'], 74.1, 3.0)
    j['note'] = (
        '순수 MR(보컬 제거) 재검수 2026-11-23 — AI 보컬 제거(vocalremover.org) 반주 3:55.73에서 '
        'CQT 크로마·저역 근음·온셋 템포를 다시 뽑았습니다. 템포는 ♩74.1(구간별 74.0~74.9)로, '
        '기존 76·하프타임 152 표기를 정정합니다. 한 마디 3.24초입니다. '
        '앞부분은 B♭장조(12초 창 0.88~0.96)로 확인되고, 후반은 3:00 무렵 창에서 C장조 0.967이 잡혀 '
        '기존의 2반음 전조(C키) 표기와 방향이 같습니다. 다만 12초 창 경계 때문에 전조 지점은 '
        '2:44~3:00 사이로만 말할 수 있고, 73마디 4박 격자는 근사입니다. '
        'major/minor·7th·sus 구분은 모델마다 갈려 청음 확인이 필요합니다.'
    )
    jehoda['chartNote'] = j['note']
    j['basis'] = (
        (j.get('basis') or '').split(' 2026-11-23')[0].strip()
        + ' 2026-11-23 순수 MR 재검수: 반주 3:55.73에서 ♩74.1(구간 74.0~74.9, 기존 76 정정)과 앞부분 B♭장조, '
          '3:00 무렵 C장조 0.967을 확인했습니다. 전조 지점은 12초 창 한계로 2:44~3:00 사이로 남깁니다.'
    )
    j['evidence'].append({
        'label': '순수 MR(보컬 제거) 실측 — media/jehoda-mr.mp3',
        'url': jehoda['videoUrl'],
        'note': 'AI 보컬 제거(vocalremover.org) 반주 3:55.73 · ♩74.1 · 앞부분 B♭장조 · 3:00 무렵 C장조 0.967',
    })
    jehoda['notes'] = (
        (jehoda['notes'].split(' 2026-11-23 순수 MR')[0]).strip()
        + ' 2026-11-23 순수 MR 재검수: AI 보컬 제거 반주로 템포를 ♩74.1로 정정하고 키·전조 위치를 다시 확인했습니다.'
    )

    # 5) verified-021 — MR 연결 + 측정값 기록(코드 진행은 유지)
    weather = by_id['verified-021']
    w = weather['chart']
    w['bpmNote'] = '순수 MR 실측 ♩90.00 (격자 탐색 0.02BPM · 30초 창 자기상관 89.98~90.11)'
    w['timeNote'] = '순수 MR 실측 — ♩90.00 · 4/4 · 한 마디 2.67초'
    w['note'] = (
        '순수 MR(보컬 제거) 재검수 2026-11-23 — AI 보컬 제거(UVR Online MDX VocFT) 반주 3:09.02에서 '
        'CQT 크로마·저역 근음·온셋 템포를 다시 뽑았습니다. ♩90.00·4/4·원키 A(전체 크로마 A장조 0.983)로 '
        '기존 값과 같습니다. 코드는 마디 격자를 MR에 다시 맞춘 대조에서 근음 일치 49/70(70%)이었고, '
        '악보 구간에 적힌 시각을 그대로 쓴 대조는 15/69로 낮았습니다 — 구간 시각이 16kbps 원본에서 '
        '어림으로 잡힌 값이라 마디 위치를 다시 볼 필요가 있습니다. '
        '가수는 여전히 미확인(#172 원칙 유지)이고, 마디별 배치와 7th·sus 성질은 청음 확인이 필요합니다.'
    )
    weather['chartNote'] = w['note']
    w['basis'] = (
        (w.get('basis') or '').split(' 2026-11-23')[0].strip()
        + ' 2026-11-23 순수 MR 재검수: 반주 3:09.02에서 ♩90.00·A장조 0.983을 확인했습니다. '
          '마디 격자를 다시 맞춘 근음 일치 49/70, 구간 시각 그대로는 15/69입니다.'
    )
    w['evidence'].append({
        'label': '순수 MR(보컬 제거) 실측 — media/weather-mr.mp3',
        'url': weather['videoUrl'],
        'note': 'AI 보컬 제거(UVR Online MDX VocFT) 반주 3:09.02 · ♩90.00 · A장조 0.983 · 근음 일치 49/70(격자 재정렬)',
    })
    weather['notes'] = (
        (weather['notes'].split(' 2026-11-23 순수 MR')[0]).strip()
        + ' 2026-11-23 순수 MR 재검수: AI 보컬 제거 반주로 ♩90.00·A장조를 확인하고 마디 격자를 다시 맞춰 대조했습니다.'
    )

    seed_path.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # 6) metadata
    with_mr = [s for s in songs if (s.get('mrUrl') or s.get('mrAudioUrl'))]
    with_yt = [s for s in with_mr if s.get('mrUrl')]
    with_local = [s for s in with_mr if s.get('mrAudioUrl')]
    works = {(s.get('workTitle') or s['title'], s.get('workArtist') or s['artist']) for s in with_mr}
    music = [s for s in songs if s['category'] != 'reference']
    meta['seedVersion'] = SEED_VERSION
    meta['chartVersion'] = DATE
    meta['mrVersion'] = DATE
    meta['mrLinkCount'] = len(with_mr)
    meta['mrWorkCount'] = len(works)
    disclosure = meta.get('mrDisclosure') or ''
    add = ('2026-11-23에는 주성 님이 AI 보컬 제거로 뽑아 보낸 반주 2건(#108 「나는 버려질 장난감」 · '
           'media/toy-mr.mp3, #172 「날씨가 좋고 바람도 좋아」 · media/weather-mr.mp3)을 추가해 '
           'MR 음원 파일 5건이 되었고, 이로써 음악 항목 162개 전부(100%)에 재생되는 반주가 연결됐습니다. ')
    if 'media/toy-mr.mp3' not in disclosure:
        disclosure = add + disclosure
    disclosure = re.sub(
        r'곡 \d+개\(서로 다른 곡 \d+개, YouTube MR 영상 \d+개 항목 \+ MR 음원 파일 \d+개 항목\)에 연결했고,',
        f'곡 {len(with_mr)}개(서로 다른 곡 {len(works)}개, YouTube MR 영상 {len(with_yt)}개 항목 + '
        f'MR 음원 파일 {len(with_local)}개 항목)에 연결했고,',
        disclosure)
    meta['mrDisclosure'] = disclosure
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    sources = json.loads((BASE / 'data' / 'source-videos.seed.json').read_text(encoding='utf-8'))
    payload = {'songs': songs, 'sources': sources, 'meta': meta}
    (BASE / 'src' / 'seed.js').write_text(
        'window.STRUM_SEED = ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')

    for name in ('index.html', 'src/app.js', 'src/styles.css'):
        p = BASE / name
        t = p.read_text(encoding='utf-8')
        p.write_text(re.sub(r'\?v=\d+', f'?v={SEED_VERSION}', t), encoding='utf-8')

    print(f'OK · seedVersion {SEED_VERSION} · MR 연결 {len(with_mr)}/{len(music)} 음악 항목 '
          f'(서로 다른 곡 {len(works)}) · YouTube {len(with_yt)} · 음원 파일 {len(with_local)}')
    print(f'   verified-017 마디 {len(old_bars)} → 49, 커피 bpm 98, jehoda bpm 74')


if __name__ == '__main__':
    main()
