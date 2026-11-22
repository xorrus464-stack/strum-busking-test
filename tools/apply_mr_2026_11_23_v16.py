#!/usr/bin/env python3
"""주성 님이 보내준 MR을 곡 데이터에 반영한다 (seed v16, 2026-11-23).

1) YouTube MR 링크 — 「잠깐 시간 될까」 두 항목(playlist-057 · playlist-058)
   https://www.youtube.com/watch?v=_aJasCmlQC8
   LEE MU JIN - Ordinary Confession (잠깐 시간 될까) (Instrumental) / Rockstar Beats
2) 저장소에 함께 올린 MR 음원 — 로꼬 「픽픽」 (playlist-157)
   주성 님이 직접 올린 화면 녹화에서 오디오만 뽑은 media/pikpik-mr.mp3 (mrAudioUrl)

동작
  - YouTube 링크는 oEmbed(HTTP 200)로 제목·채널을 다시 확인한다
  - data/metadata.json 의 mrLinkCount·mrWorkCount 를 실제 데이터에서 다시 센다(MR 영상 + MR 음원 모두)
  - seedVersion 15 → 16, index.html·styles.css·app.js·seed.js 의 ?v= 도 16
  - 기존 연습 기록·직접 수정값은 건드리지 않는다(src/seed.js 만 다시 씀)

실행: python3 tools/apply_mr_2026_11_23_v16.py
"""
import json
import pathlib
import re
import urllib.parse
import urllib.request

BASE = pathlib.Path(__file__).resolve().parents[1]
SEED_VERSION = 16
DATE = '2026-11-23'

YT_VIDEO = '_aJasCmlQC8'
YT_IDS = ['playlist-057', 'playlist-058']

LOCAL_MR = 'media/pikpik-mr.mp3'
LOCAL_IDS = ['playlist-157']


def oembed(vid):
    q = urllib.parse.quote(f'https://www.youtube.com/watch?v={vid}', safe='')
    req = urllib.request.Request(f'https://www.youtube.com/oembed?url={q}&format=json',
                                 headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        assert r.status == 200, (vid, r.status)
        d = json.loads(r.read().decode('utf-8'))
    return d['title'], d['author_name']


def main():
    seed_path = BASE / 'data' / 'songs.seed.json'
    meta_path = BASE / 'data' / 'metadata.json'
    songs = json.loads(seed_path.read_text(encoding='utf-8'))
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    by_id = {s['id']: s for s in songs}

    # 1) YouTube MR — 잠깐 시간 될까 두 항목
    title, channel = oembed(YT_VIDEO)
    for sid in YT_IDS:
        s = by_id[sid]
        s['mrUrl'] = f'https://www.youtube.com/watch?v={YT_VIDEO}'
        s['mrTitle'] = title
        s['mrChannel'] = channel
        s['mrNote'] = (f'{channel} · 주성 님 지정 · 잠깐 시간 될까 Instrumental · '
                       f'YouTube oEmbed 200 + 임베드 재생 확인({DATE})')
        s['mrSource'] = 'youtube'
        print(f'{sid}: {title} / {channel}')

    # 2) 저장소 음원 MR — 픽픽
    mp3 = BASE / LOCAL_MR
    assert mp3.exists() and mp3.stat().st_size > 1_000_000, ('MR 음원 없음', str(mp3))
    for sid in LOCAL_IDS:
        s = by_id[sid]
        s['mrAudioUrl'] = LOCAL_MR
        s['mrTitle'] = '로꼬 (LOCO) - 픽픽 (PICK PICK) TJ 84960 멜로디제거 반주 (주성 님 녹화)'
        s['mrNote'] = (f'주성 님이 2026-11-22 화면 녹화로 올린 반주에서 오디오만 추출 · '
                       f'{LOCAL_MR} ({mp3.stat().st_size // 1024}KB) · 미니 플레이어에서 바로 재생({DATE})')
        s['mrSource'] = 'user-recording'
        print(f'{sid}: {LOCAL_MR} ({mp3.stat().st_size} bytes)')

    seed_path.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # MR 집계는 실제 데이터에서 다시 센다(곡 단위·서로 다른 곡 단위). MR 영상과 MR 음원 파일을 모두 센다.
    with_mr = [s for s in songs if (s.get('mrUrl') or s.get('mrAudioUrl'))]
    with_yt = [s for s in with_mr if s.get('mrUrl')]
    with_local = [s for s in with_mr if s.get('mrAudioUrl')]
    works = {(s.get('workTitle') or s['title'], s.get('workArtist') or s['artist']) for s in with_mr}
    meta['seedVersion'] = SEED_VERSION
    meta['mrVersion'] = DATE
    meta['mrLinkCount'] = len(with_mr)
    meta['mrWorkCount'] = len(works)
    meta['mrDisclosure'] = (
        'MR(반주) 링크는 YouTube 검색 결과에서 제목에 MR·Inst·노래방·반주 표기가 있고 YouTube oEmbed HTTP 200으로 존재를 확인한 뒤, '
        '앱과 같은 iframe 플레이어로 임베드 재생까지 확인한 영상만 연결했습니다. '
        'TJ노래방 공식 채널은 임베드 재생을 막아(플레이어 오류 150) 금영(KY)·엠알샵·싱잇·MR노래방·여기MR·아티스트 공식 inst. 등 재생되는 반주로 바꿨습니다. '
        '2026-11-23에는 주성 님이 직접 보내준 4건(#77 사랑이라 믿었던 것들은 · #144 기억을 걷는 시간 · #24 에아오 · #166 Feel Special 피아노 반주)을 '
        '같은 방식으로 확인해 추가했고, 이어 「잠깐 시간 될까」 두 항목에 LEE MU JIN Ordinary Confession Instrumental(Rockstar Beats)을 연결했습니다. '
        '주성 님이 직접 올린 녹화에서 오디오만 추출한 반주(로꼬 픽픽 · media/pikpik-mr.mp3)는 MR 음원 파일로 연결해 미니 플레이어 안에서 바로 재생합니다. '
        f'곡 {len(with_mr)}개(서로 다른 곡 {len(works)}개, YouTube MR 영상 {len(with_yt)}개 항목 + MR 음원 파일 {len(with_local)}개 항목)에 연결했고, '
        '재생되는 반주가 확인되지 않은 곡은 비워 두어 화면에서 MR 없음으로 표시한 뒤 YouTube MR 검색과 URL 붙여넣기로 직접 등록할 수 있게 했습니다.'
    )
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
