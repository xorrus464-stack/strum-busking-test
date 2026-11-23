#!/usr/bin/env python3
"""「10,000 Hours」 MR을 밈 영상에서 실제 연주 가라오케로 교체한다 (seed v19, 2026-11-23).

배경: added-10000-hours 의 MR 로 연결돼 있던 ChaoticBrooke
「10,000 hours by Dan And Shay(Karaoke Version)🔥」(Gt636FM6Ayc) 는 실제 반주가 아닌
밈·스킷 영상(썸네일·영상 모두 술자리 스킥)이어서 주성 님이 "이상한 영상"이라고 지적했다.

검증(2026-11-23, 라이브 페이지 https://xorrus464-stack.github.io/strum-busking-test/ 의
mrcheck 임시 페이지에서 앱과 같은 iframe 플레이어로 확인):
  - oEmbed 200: IUWyNhWJCTU, HxtLoi42ano, vBLCXuDeQO8, Gt636FM6Ayc (4건 모두)
  - 임베드 재생(PLAYS): HxtLoi42ano(Mifta Acoustic Project), vBLCXuDeQO8(MrEntertainerKaraoke)
  - 임베드 차단(ERROR150): XVG-jODTeyQ(Sing King), a2pdhQFG_7A(Sing2Guitar),
    wms8Zb3BOPo(KaraFun), 3건 모두 "동영상 소유자가 다른 웹사이트에서 재생할 수 없도록 설정"
  - 끝까지 재생 상태로 넘어오지 않음(TIMEOUT): IUWyNhWJCTU(YAYY)
→ 실제 악기로 만든 MrEntertainerKaraoke 가라오케(vBLCXuDeQO8)로 교체.

seedVersion 18 → 19, src/seed.js 재생성, index.html·app.js·styles.css ?v=19.

실행: python3 tools/apply_mr_2026_11_23_v19.py
"""
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parents[1]
SEED_VERSION = 19
DATE = '2026-11-23'

SONG_ID = 'added-10000-hours'
NEW = {
    'mrUrl': 'https://www.youtube.com/watch?v=vBLCXuDeQO8',
    'mrTitle': '10,000 Hours - Dan + Shay & Justin Bieber (KARAOKE)',
    'mrChannel': 'MrEntertainerKaraoke',
    'mrNote': ('MrEntertainerKaraoke · 실제 악기로 만든 원키 가라오케(3:03) · '
               'YouTube oEmbed 200 + 임베드 재생 확인(2026-11-23)'),
    'mrSource': 'youtube',
}
ADD_NOTE = (
    ' 2026-11-23 MR 교체: 기존 ChaoticBrooke 「10,000 hours by Dan And Shay(Karaoke Version)」'
    '(Gt636FM6Ayc)는 반주가 아닌 밈·스킷 영상이라, 실제 악기로 만든 MrEntertainerKaraoke '
    '가라오케(vBLCXuDeQO8, 3:03)로 바꿨습니다. 앱 하단 미니 플레이어에서 재생되는 것을 확인했습니다. '
    '악보는 주성 님이 올린 MR(A장조·86.1 BPM)에 맞춰져 있어, 원곡 키(B♭)·템포(90) 기준 가라오케와는 '
    '1반음·약 4 BPM 차이가 날 수 있습니다(청음 확인 전).'
)


def main():
    seed_path = BASE / 'data' / 'songs.seed.json'
    meta_path = BASE / 'data' / 'metadata.json'
    songs = json.loads(seed_path.read_text(encoding='utf-8'))
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    by_id = {s['id']: s for s in songs}
    song = by_id[SONG_ID]

    old_url = song.get('mrUrl')
    assert old_url and old_url.endswith('Gt636FM6Ayc'), old_url
    # 새 MR 이 다른 곡에 쓰이지 않았는지 확인 (같은 곡은 같은 MR 규칙)
    assert not any(s.get('mrUrl') == NEW['mrUrl'] for s in songs), '새 MR 중복'
    song.update(NEW)
    assert '2026-11-23 MR 교체' not in song['notes'], '이미 반영됨'
    song['notes'] = song['notes'].rstrip() + ADD_NOTE

    seed_path.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # metadata — 집계는 그대로(교체), 버전만 올리고 교체 사실을 남긴다
    with_mr = [s for s in songs if (s.get('mrUrl') or s.get('mrAudioUrl'))]
    with_yt = [s for s in with_mr if s.get('mrUrl')]
    with_local = [s for s in with_mr if s.get('mrAudioUrl')]
    works = {(s.get('workTitle') or s['title'], s.get('workArtist') or s['artist']) for s in with_mr}
    music = [s for s in songs if s['category'] != 'reference']
    assert len(with_mr) == 162 and len(with_yt) == 157 and len(with_local) == 5
    assert len(works) == 135 and len(music) == 162
    meta['seedVersion'] = SEED_VERSION
    meta['mrVersion'] = DATE
    meta['mrLinkCount'] = len(with_mr)
    meta['mrWorkCount'] = len(works)
    disclosure = meta.get('mrDisclosure') or ''
    if 'vBLCXuDeQO8' not in disclosure:
        disclosure = ('2026-11-23: 「10,000 Hours」의 MR 이 반주가 아닌 밈·스킷 영상'
                      '(ChaoticBrooke Gt636FM6Ayc)이어서 실제 악기로 만든 MrEntertainerKaraoke '
                      '가라오케(vBLCXuDeQO8, oEmbed 200 + 임베드 재생 확인)로 교체했습니다. '
                      '같은 날 후보 6건을 앱과 같은 iframe 플레이어로 확인해 Sing King·Sing2Guitar·'
                      'KaraFun 은 임베드 차단(오류 150), YAYY 는 재생 확인 실패로 제외했습니다. ') + disclosure
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

    print(f'OK · seedVersion {SEED_VERSION} · {SONG_ID} MR → {NEW["mrUrl"]} ({NEW["mrChannel"]})')
    print(f'   MR 연결 {len(with_mr)}/{len(music)} 음악 항목 · 서로 다른 곡 {len(works)} · '
          f'YouTube {len(with_yt)} · 음원 파일 {len(with_local)}')


if __name__ == '__main__':
    main()
