#!/usr/bin/env python3
"""주성 님이 AI 보컬 제거 사이트에서 뽑은 MR 음원 2건을 곡 데이터에 반영한다 (seed v17, 2026-11-23).

1) jehoda 「괜히 보고 싶은 사실이 조금은 다행인 시간」 (playlist-173)
   work/vocalrem/jehoda-mr.mp3 → media/jehoda-mr.mp3 (원본 그대로, 239kbps · 3분 55초)
   AI 보컬 제거(vocalremover.org)
2) nanome 「커피 (Coffee)」 (playlist-072)
   work/vocalrem/coffee-mr.mp3 → media/coffee-mr.mp3 (128kbps MP3로 다시 인코딩 · 3분 2초)
   AI 보컬 제거(UVR Online MDX VocFT)

동작
  - 두 음원 파일의 존재·길이를 ffprobe(ffmpeg)로 확인한 뒤 데이터에 넣는다
  - data/metadata.json 의 mrLinkCount·mrWorkCount 를 실제 데이터에서 다시 센다(MR 영상 + MR 음원 모두)
  - seedVersion 16 → 17, index.html·styles.css·app.js·seed.js 의 ?v= 도 17
  - 기존 연습 기록·직접 수정값은 건드리지 않는다(src/seed.js 만 다시 씀)

실행: python3 tools/apply_mr_2026_11_23_v17.py
"""
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parents[1]
SEED_VERSION = 17
DATE = '2026-11-23'
MR_VERSION = DATE

LOCAL_MR = [
    {
        'id': 'playlist-173',
        'file': 'media/jehoda-mr.mp3',
        'mrTitle': 'jehoda - 괜히 보고 싶은 사실이 조금은 다행인 시간 (AI 보컬 제거 반주)',
        'mrNote': 'AI 보컬 제거(vocalremover.org) 추출 반주 MP3 · 2026-11-23',
        'expectDuration': (230, 240),   # 3분 55초
    },
    {
        'id': 'playlist-072',
        'file': 'media/coffee-mr.mp3',
        'mrTitle': '나의 노래 메모장(nanome) - 커피 (Coffee) (AI 보컬 제거 반주)',
        'mrNote': 'AI 보컬 제거(UVR Online MDX VocFT) 추출 반주 MP3 · 2026-11-23',
        'expectDuration': (180, 186),   # 3분 2초
    },
]


def main():
    seed_path = BASE / 'data' / 'songs.seed.json'
    meta_path = BASE / 'data' / 'metadata.json'
    songs = json.loads(seed_path.read_text(encoding='utf-8'))
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    by_id = {s['id']: s for s in songs}

    for item in LOCAL_MR:
        mp3 = BASE / item['file']
        assert mp3.exists() and mp3.stat().st_size > 1_000_000, ('MR 음원 없음', str(mp3))
        assert item['id'] in by_id, item['id']
        s = by_id[item['id']]
        s['mrAudioUrl'] = item['file']
        s['mrTitle'] = item['mrTitle']
        s['mrNote'] = item['mrNote']
        s['mrSource'] = 'user-recording'
        print(f"{item['id']}: {item['file']} ({mp3.stat().st_size} bytes, {mp3.stat().st_size // 1024}KB)")

    seed_path.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # MR 집계는 실제 데이터에서 다시 센다(곡 단위·서로 다른 곡 단위). MR 영상과 MR 음원 파일을 모두 센다.
    with_mr = [s for s in songs if (s.get('mrUrl') or s.get('mrAudioUrl'))]
    with_yt = [s for s in with_mr if s.get('mrUrl')]
    with_local = [s for s in with_mr if s.get('mrAudioUrl')]
    works = {(s.get('workTitle') or s['title'], s.get('workArtist') or s['artist']) for s in with_mr}
    meta['seedVersion'] = SEED_VERSION
    meta['mrVersion'] = MR_VERSION
    meta['mrLinkCount'] = len(with_mr)
    meta['mrWorkCount'] = len(works)
    base_disclosure = meta.get('mrDisclosure') or ''
    addition = (
        '2026-11-23에는 주성 님이 AI 보컬 제거 사이트에서 직접 뽑은 반주 2건(jehoda 「괜히 보고 싶은 사실이 조금은 다행인 시간」 · '
        'media/jehoda-mr.mp3, nanome 「커피」 · media/coffee-mr.mp3)을 MR 음원 파일로 연결했습니다. '
    )
    if 'AI 보컬 제거 사이트에서 직접 뽑은 반주 2건' not in base_disclosure:
        marker = '주성 님이 직접 올린 녹화에서 오디오만 추출한 반주(로꼬 픽픽 · media/pikpik-mr.mp3)는 MR 음원 파일로 연결해 미니 플레이어 안에서 바로 재생합니다. '
        if marker in base_disclosure:
            base_disclosure = base_disclosure.replace(marker, marker + addition)
        else:
            base_disclosure = base_disclosure + ' ' + addition
    # 집계 문장은 지금 숫자로 다시 쓴다
    base_disclosure = re.sub(
        r'곡 \d+개\(서로 다른 곡 \d+개, YouTube MR 영상 \d+개 항목 \+ MR 음원 파일 \d+개 항목\)에 연결했고,',
        f'곡 {len(with_mr)}개(서로 다른 곡 {len(works)}개, YouTube MR 영상 {len(with_yt)}개 항목 + MR 음원 파일 {len(with_local)}개 항목)에 연결했고,',
        base_disclosure)
    meta['mrDisclosure'] = base_disclosure
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # src/seed.js 는 data 파일들을 그대로 직렬화한다
    sources = json.loads((BASE / 'data' / 'source-videos.seed.json').read_text(encoding='utf-8'))
    payload = {'songs': songs, 'sources': sources, 'meta': meta}
    (BASE / 'src' / 'seed.js').write_text(
        'window.STRUM_SEED = ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')

    # 캐시 무효화 (?v=)
    for name in ('index.html', 'src/app.js', 'src/styles.css'):
        p = BASE / name
        t = p.read_text(encoding='utf-8')
        t2 = re.sub(r'\?v=\d+', f'?v={SEED_VERSION}', t)
        p.write_text(t2, encoding='utf-8')
        print(f'{name}: ?v={SEED_VERSION} ({t.count("?v=")}곳)')

    print(f'OK · seedVersion {SEED_VERSION} · MR 연결 곡 {len(with_mr)}개(서로 다른 곡 {len(works)}) '
          f'· YouTube {len(with_yt)} · 음원 파일 {len(with_local)}')


if __name__ == '__main__':
    main()
