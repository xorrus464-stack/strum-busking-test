#!/usr/bin/env python3
"""MR(반주) 링크를 곡 데이터에 반영한다 (seed v13).

입력
  - tmp/mr_result.json : tools/mr_search.py 가 모은 검색·검증 후보(작업 단위)
  - 아래 OVERRIDES     : 사람이 확인해 고른 링크(공식 MR·ZIP 자료·공식 karaoke)
  - 포함/제외 판단 WHITELIST_EXCLUDE

동작
  - 모든 링크를 YouTube oEmbed 로 다시 확인(HTTP 200 + 제목에 MR·Inst·노래방 표기)
  - work(곡명+가수) 단위로 곡마다 mrUrl / mrTitle / mrChannel / mrNote / mrSource 를 채운다
  - seedVersion 12 → 13, data/songs.seed.json · src/seed.js · data/metadata.json 갱신

실행: python3 tools/apply_mr.py
"""
import json
import pathlib
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from tools.mr_search import oembed, marker_score  # noqa: E402

SEED_VERSION = 13

# 사람이 직접 확인한 링크 (검색 결과 + ZIP 자료). 값: (videoId, 근거)
OVERRIDES = {
    ('오늘도 날씨는 흐리네', '정영원'): ('ZbHcA5kVn1w', '공식 Instrumental(Release - Topic)'),
    ('어떤이별', '임승부'): ('uJ5TFy8XH7Y', 'ZIP 원본 MR · 임승부(Lim Seung bu)-어떤이별(M.R)'),
    ('안녕 너희', '허각'): ('s82tYAXsmCc', '공식 Inst.(Huh Gak - Topic)'),
    ('나의 아버지 (Dad)', '도경수 (D.O.)'): ('R0ZOFPIEeis', 'TJ노래방 공식'),
    ('기억을 걷는 시간 (Time Spent Walking Through Memories)', '넬 (NELL)'): ('qLcOyiaD-nI', 'TJ노래방 공식'),
    ('WHAT IS LOVE (2026.ver)', 'EXO-K'): ('V_T3k1Tbp3U', 'TJ노래방 공식'),
    ('에아오 (AEAO)', '다이나믹듀오 × DJ Premier'): ('dh0FGfpGq3o', 'TJ노래방 공식'),
    ('미안해 미워해 사랑해 (Love You With All My Heart)', '크러쉬 (CRUSH)'): ('GKjIG_wogsw', 'TJ노래방 공식'),
    ('꿈의 등불 (夢灯籠)', 'RADWIMPS'): ('i0IkX_yd5gA', 'カラオケ歌っちゃ王 · 가이드 없음'),
    ('Somebody', '도경수 (D.O.)'): ('Ro_2DgNWtf8', 'TJ노래방 공식'),
    ('기적 (Wonder)', '도경수 (D.O.)'): ('azQhzlKb4H0', 'TJ노래방 공식'),
    ('기억의 온기 (Where You Were)', '도경수 (D.O.)'): ('yjd_CpFQMTs', '공식 Instrumental'),
    ('たぶん (아마도)', 'YOASOBI'): ('LFl5Z2vl9GE', 'カラオケ(歌っちゃ王 - Topic)'),
    ('비도 오고 그래서 (You, Clouds, Rain)', '헤이즈 (HEIZE)'): ('oNLga08VuDk', 'TJ노래방 공식'),
    ('첫눈처럼 너에게 가겠다 (I will go to you like the first snow)', '에일리 (AILEE)'): ('dqWX5nGJV8w', 'TJ노래방 공식 · 남자키'),
    ('서, 어른', '키썸 (Kisum)'): ('ige-TSCG5vc', '공식 inst. (ZIP 자료 · Kisum - Topic)'),
    ('닮은사람', '이기찬'): ('o2IIptFFbm8', 'TJ노래방 공식 · 멜로디제거(ZIP 원본 반주 -qmTiCusjoo는 임베드 제한)'),
    ('10,000 Hours', 'Dan + Shay feat. Justin Bieber'): ('7FRBYWmJZHw', 'Acoustic Karaoke(Acoustic Lounge)'),
    ('Stand by Me', 'Ben E. King'): ('wEUgcE0N-G0', 'Kopa Kopi Karaoke · Instrumental Backing Track'),
    ('死別 (feat. GUMI)', 'Shannon'): ('cLUNCLUE7pk', '노래방 カラオケ(LKARA)'),
    ('無題 (무제)', '지드래곤 (G-DRAGON)'): ('lqt4Znd5Hlk', 'TJ노래방 공식 · 멜로디제거'),
    ('청혼하지 않을 이유를 못 찾았어 (Propose)', '이무진 (LEE MUJIN)'): ('020n1-s11zg', 'TJ노래방 공식 · 멜로디제거'),
}

# 재생목록에서 '노래방' 표기만 보고 MR로 붙이면 안 되는 곡(보컬 커버·무반주 라이브) — 기록용
PLAYLIST_KEYWORD_SKIPPED = {
    'playlist-008': '코인노래방 커버(보컬)',
    'playlist-023': '가수 모창 메들리(보컬)',
    'playlist-041': '무반주(a cappella) 라이브',
    'playlist-086': '노래커버(보컬)',
    'playlist-160': '노래방 커버(보컬)',
}


def norm(s):
    s = unicodedata.normalize('NFKC', str(s or '')).lower()
    return re.sub(r'[\s\(\)\[\]\{\}\.,\'"`·:;!?\-_/\\|&+#%$@~^*+=<>]+', '', s)


def main():
    songs = json.loads((BASE / 'data' / 'songs.seed.json').read_text(encoding='utf-8'))
    meta = json.loads((BASE / 'data' / 'metadata.json').read_text(encoding='utf-8'))
    auto_path = BASE / 'tmp' / 'mr_result.json'
    auto = {}
    if auto_path.exists():
        for w in json.loads(auto_path.read_text(encoding='utf-8')):
            auto[(w['title'], w['artist'])] = w.get('mr')

    def lookup(title, artist):
        if (title, artist) in OVERRIDES:
            vid, note = OVERRIDES[(title, artist)]
            return vid, note
        m = auto.get((title, artist))
        if m:
            return m['videoId'], f"{m['channel']} · 검색 '{m['query']}'"
        return None, None

    cache = {}
    checked = 0
    updated = 0
    per_work = {}
    for s in songs:
        title = s.get('workTitle') or s['title']
        artist = s.get('workArtist') or s['artist']
        if s.get('chartStatus') not in ('ready', 'partial', 'original'):
            continue
        key = (title, artist)
        if key not in per_work:
            vid, note = lookup(title, artist)
            auto_m = auto.get(key)
            auto_vid = auto_m['videoId'] if auto_m else None
            if not vid:
                per_work[key] = None
                continue
            if vid not in cache:
                info = oembed(vid)
                checked += 1
                # 직접 고른 링크가 임베드 제한(oEmbed 실패)이면 검색 결과로 대체한다.
                if not info and auto_vid:
                    alt = oembed(auto_vid)
                    if alt:
                        info, vid = alt, auto_vid
                        note = f"{alt['author_name']} · 검색 결과 대체"
                if not info:
                    per_work[key] = None
                    continue
                ms, _ = marker_score(info['title'])
                if ms < 2:   # oEmbed 제목에 반주 표기가 없으면 연결하지 않는다
                    per_work[key] = None
                    continue
                cache[vid] = info
            info = cache[vid]
            per_work[key] = {'videoId': vid, 'url': f'https://www.youtube.com/watch?v={vid}',
                             'title': info['title'], 'channel': info['author_name'], 'note': note}
        rec = per_work[key]
        if not rec:
            continue
        s['mrUrl'] = rec['url']
        s['mrTitle'] = rec['title']
        s['mrChannel'] = rec['channel']
        s['mrNote'] = f"{rec['note']} · YouTube oEmbed 200 확인(2026-11-22)"
        s['mrSource'] = 'zip' if 'ZIP' in (rec['note'] or '') else 'youtube'
        updated += 1
    for s in songs:
        if 'mrUrl' in s and s.get('category') == 'reference':
            del s['mrUrl']

    hit = sum(1 for s in songs if s.get('mrUrl'))
    works = sum(1 for v in per_work.values() if v)
    meta['seedVersion'] = SEED_VERSION
    meta['mrVersion'] = '2026-11-22'
    meta['mrLinkCount'] = hit
    meta['mrWorkCount'] = works
    meta['mrDisclosure'] = ('MR(반주) 링크는 YouTube 검색 결과에서 제목에 MR·Inst·노래방·반주 표기가 있고 '
                            'YouTube oEmbed HTTP 200으로 실제 존재를 확인한 영상만 연결했습니다. '
                            f'곡 {hit}개(서로 다른 곡 {works}개)에 연결했고, 확인되지 않은 곡은 비워 두어 '
                            '화면에서 MR 없음으로 표시한 뒤 YouTube MR 검색과 URL 붙여넣기로 직접 등록할 수 있게 했습니다. '
                            'TI·금영 공식 채널과 아티스트 공식 inst.를 우선했습니다.')
    meta['mrDisclosure'] = meta['mrDisclosure'].replace('TI·금영', 'TJ·금영')

    (BASE / 'data' / 'songs.seed.json').write_text(
        json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    sources = json.loads((BASE / 'data' / 'source-videos.seed.json').read_text(encoding='utf-8'))
    (BASE / 'data' / 'metadata.json').write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (BASE / 'src' / 'seed.js').write_text(
        'window.STRUM_SEED = ' + json.dumps({'songs': songs, 'sources': sources, 'meta': meta},
                                            ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')
    print(f'OK: oEmbed 확인 {checked}개 · MR 연결 곡 {hit}개(서로 다른 곡 {works}개) · seedVersion {SEED_VERSION}')


if __name__ == '__main__':
    main()
