#!/usr/bin/env python3
"""여자 원곡 43개 항목의 MR·음악 영상을 남자키 기준으로 정리한다 (seed v20, 2026-11-23).

1) MR(반주) — 여자 원곡(key != maleKey) 항목을 '남자키 MR'로 교체
   · 후보 수집: YouTube 검색('{곡} 남자키 MR', '{곡} 남키 노래방' 등)
   · 통과 조건: YouTube oEmbed HTTP 200 + 임베드 재생 가능(앱과 같은 iframe 플레이어 기준)
     + TJ노래방 공식 채널 제외(임베드 차단, 오류 150)
   · 남자키 MR을 찾지 못한 곡은 기존 MR을 두고 mrNote 에 '[원키 MR · -5키 필요]' 를 남긴다.
2) 음악 영상(videoUrl) — 여자 보컬·쇼츠/맛보기 영상은 남자 풀커버(완창) 영상으로 교체.
3) seedVersion 20 · index.html/app.js/styles.css ?v=20 · sw.js 캐시 이름 v2

검증 기록은 docs/MR_남자키_교체_2026-11-23.md 에 남긴다.

실행: python3 tools/apply_mr_female_male_key_2026_11_23.py
"""
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parents[1]
SEED_VERSION = 20
DATE = '2026-11-23'

# ── MR 교체: 곡 id → (유튜브 id, 표기) ────────────────────────────────────────
MR = {
    'verified-002': ('iQG-zBBCnDE', '남자 버전 반주(B.B Factory, Acoustic Inst/MR)'),
    'verified-007': ('VnSBIixg7hY', '금영 공식 남자키 노래방(KY.78657)'),
    'verified-010': ('oJp_AdZ3wXw', '남자키 어쿠스틱 MR(MR. Acoustic, Key D♭)'),
    'restored-119': ('zXIkIg9S_yE', '남자키 MR(여기MR, G♯m/-5)'),
    'restored-130': ('rVbefGSL9NY', '금영 공식 남자키(KY.76229)'),
    'restored-151': ('TH5oJvKPmRw', '남자키 노래방(Karaoke : Male Key)'),
    'restored-100': ('YVbcUiPMBPM', '공식 인스트루멘탈(원키·가이드멜로디 없음)'),
    'restored-131': ('6tFsFWLy2wk', '남자키 MR(여기MR, E/-5)'),
    'playlist-156': ('6tFsFWLy2wk', '남자키 MR(여기MR, E/-5)'),
    'restored-132': ('z1Hec1DHN6c', '남자키 MR(여기MR, D/-5)'),
    'playlist-062': ('z1Hec1DHN6c', '남자키 MR(여기MR, D/-5)'),
    'playlist-004': ('A0Oco_fYmmE', '남자키 MR(볼트, -5키)'),
    'playlist-031': ('GHQf2rXz8p8', '금영 공식 남자키(KY.22298)'),
    'playlist-032': ('6gxt0c8dMNw', '남자키 MR(여기MR, B♭/-5)'),
    'playlist-033': ('6gxt0c8dMNw', '남자키 MR(여기MR, B♭/-5)'),
    'playlist-188': ('6gxt0c8dMNw', '남자키 MR(여기MR, B♭/-5)'),
    'playlist-208': ('6gxt0c8dMNw', '남자키 MR(여기MR, B♭/-5)'),
    'playlist-035': ('bqsDbTmxzOM', '남자키 어쿠스틱 MR(MR. Acoustic, Key E♭)'),
    'playlist-036': ('bqsDbTmxzOM', '남자키 어쿠스틱 MR(MR. Acoustic, Key E♭)'),
    'playlist-054': ('Zo5Gegjm7sk', '남자키(-5키) 영상 MR'),
    'playlist-073': ('eZJN3qCT0Iw', '남자키(-2) 오프보컬(가이드멜로디 없음)'),
    'playlist-075': ('1jM1_kzfFc4', '남자키 MR(하다지, A단조)'),
    'playlist-084': ('BtzJ_S98gWQ', '금영 공식 남자키(KY.24277)'),
    'playlist-085': ('BtzJ_S98gWQ', '금영 공식 남자키(KY.24277)'),
    'playlist-092': ('--TRRB1SfLw', '금영 공식 남자키(KY.22807)'),
    'playlist-111': ('Zh0tkyRV5vw', '금영 공식 남자키(KY.1812)'),
    'playlist-160': ('RWwVa_wLJnc', '금영 공식 남자키(KY.80672)'),
    'playlist-165': ('-rmv-QSH-r0', '남자키(-5키) 노래방'),
    'playlist-166': ('cbkluSvv758', '남자키 MR(Man Ver.)'),
    'playlist-175': ('ffEQBhegrlo', '금영 공식 남자키(KY.57828)'),
    'playlist-194': ('8cpfnHf-Gmw', '금영 공식 남자키(KY.80872)'),
}

# 남자키 MR을 찾지 못해 기존 MR을 유지하는 곡 — mrNote 에 사유를 남긴다
KEEP_ANNOTATE = {
    'restored-100': '[원키 MR · -5키 필요]',
    'verified-014': '[원키 MR · -5키 필요]',
    'verified-019': '[원키 MR · -5키 필요]',
    'playlist-170': '[원키 MR · -5키 필요]',
    'playlist-174': '[원키 MR · -5키 필요]',
    'playlist-159': '[원키 MR · -5키 필요]',
}

# ── 음악 영상(videoUrl) 교체: 곡 id → (유튜브 id, 상태 표기) ──────────────────
VIDEO = {
    'verified-007': ('FP67e2l_KJs', '공개 영상(남자 커버)'),
    'verified-010': ('YtHsa4eC388', '공개 영상(남자 커버)'),
    'verified-014': ('JrFMYs2PU_s', '공개 영상(남자키 커버)'),
    'verified-019': ('xp6M9wtMIxM', '공개 영상(남자 커버)'),
    'restored-096': ('HDe9zjs6ajQ', '공개 영상(남자 커버)'),
    'restored-100': ('aJIGwku9UlE', '공개 영상(남자 커버)'),
    'restored-119': ('a9KDWjTi6OA', '공개 영상(남자 커버)'),
    'restored-128': ('9wBlRkKYlzs', '공개 영상(남자 커버)'),
    'restored-130': ('2OBF8S_BQu0', '공개 영상(남자 커버)'),
    'restored-131': ('spQmMNSaxZQ', '공개 영상(남자 커버)'),
    'restored-132': ('49pBS6s8avc', '공개 영상(남자 커버)'),
    'restored-151': ('_cOPV_XTpqs', '공개 영상(남자 커버)'),
    'playlist-004': ('k6lxnKSTkcs', '공개 영상(남자 커버)'),
    'playlist-032': ('8TAYDUleGBQ', '공개 영상(남자 커버)'),
    'playlist-054': ('1hz2rEp_D8s', '공개 영상(남자 커버)'),
    'playlist-084': ('WzI1qz1wZY4', '공개 영상(남자 커버)'),
    'playlist-165': ('xblo0lg5rPE', '공개 영상(남자 커버)'),
    'playlist-166': ('O_ezc_3D7iE', '공개 영상(남자 그룹 라이브 커버)'),
    'playlist-170': ('b9nbgXmYjBI', '공개 영상(남자 답가 커버)'),
    'playlist-174': ('to3sjq-CAvA', '공개 영상(진영&최유리 풀버전)'),
    'playlist-175': ('NE7TPaHWs5Q', '공개 영상(남자 커버)'),
}


def main():
    songs_path = BASE / 'data' / 'songs.seed.json'
    meta_path = BASE / 'data' / 'metadata.json'
    songs = json.loads(songs_path.read_text(encoding='utf-8'))
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    by_id = {s['id']: s for s in songs}
    oembed = json.loads((BASE / 'tmp' / 'cand_oembed.json').read_text(encoding='utf-8'))

    female = [s for s in songs if s['category'] != 'reference' and s.get('key') != s.get('maleKey')]
    assert len(female) == 43, len(female)

    # 1) MR 교체 (같은 곡이 여러 항목이면 같은 MR 을 쓴다 — works 규칙)
    used_urls = {}
    for sid, (vid, label) in MR.items():
        s = by_id[sid]
        meta_o = oembed.get(vid)
        assert meta_o, (sid, vid, 'oEmbed 확인값 없음')
        url = f'https://www.youtube.com/watch?v={vid}'
        work_key = (s.get('workTitle') or s['title'], s.get('workArtist') or s['artist'])
        if url in used_urls:
            assert used_urls[url] == work_key, ('다른 곡에 같은 MR', sid, work_key, used_urls[url])
        used_urls[url] = work_key
        old = s.get('mrTitle') or ''
        s['mrUrl'] = url
        s['mrTitle'] = meta_o['title']
        s['mrChannel'] = meta_o['author']
        s['mrNote'] = f"{meta_o['author']} · {label} · YouTube oEmbed 200 + 임베드 재생 확인(2026-11-23)"
        s['mrSource'] = 'youtube'
        s.pop('mrEdited', None)
        s['notes'] = s['notes'].rstrip() + (
            f" 2026-11-23 남자키 MR 교체: 기존 「{old}」 대신 {meta_o['author']} "
            f"「{meta_o['title']}」({vid})로 바꿨습니다(원곡이 여성 키인 곡).")

    # 2) 기존 MR 유지 + 원키 표시
    for sid, tag in KEEP_ANNOTATE.items():
        s = by_id[sid]
        note = s.get('mrNote') or ''
        assert tag not in note
        s['mrNote'] = (note + ' ' + tag).strip()

    # 3) 음악 영상 교체 (영상 주소는 곡마다 하나 — 중복 금지)
    existing = {s['videoUrl'] for s in songs if s.get('videoUrl')}
    for sid, (vid, status) in VIDEO.items():
        s = by_id[sid]
        url = f'https://www.youtube.com/watch?v={vid}'
        assert url not in existing, ('영상 주소 중복', sid, vid)
        existing.discard(s['videoUrl'])
        existing.add(url)
        old = s['videoUrl']
        s['videoUrl'] = url
        s['videoStatus'] = status
        s['notes'] = s['notes'].rstrip() + (
            f" 2026-11-23 음악 영상 교체: 여자 보컬·쇼츠/맛보기 영상({old.rsplit('=', 1)[-1]}) 대신 "
            f"남자 풀커버 {vid} 로 바꿨습니다.")

    songs_path.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # 4) metadata
    meta['seedVersion'] = SEED_VERSION
    meta['mrVersion'] = DATE
    meta['videoLinkFilledCount'] = 36
    mr_disc = meta.get('mrDisclosure') or ''
    add = ('2026-11-23: 여자 원곡 항목은 「남자키 MR」 기준으로 다시 맞췄습니다. 곡별로 YouTube 검색 → '
           'oEmbed 200 → 앱과 같은 iframe 플레이어 임베드 재생 확인을 거쳐 남자키 MR을 찾은 곡은 교체했고'
           '(금영 공식 남자키·여기MR 남자키·MR. Acoustic 남Key 등), TJ노래방 공식 채널은 임베드가 막혀'
           '(오류 150) 제외했습니다. 끝내 남자키 MR이 없는 곡은 기존 반주를 두고 mrNote 에 '
           '"[원키 MR · -5키 필요]"를 적었습니다. 남자 풀커버 영상이 있는 곡은 음악 영상도 남자 완창 영상으로 바꿨습니다. ')
    if '남자키 MR」 기준으로' not in mr_disc:
        meta['mrDisclosure'] = add + mr_disc
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # 5) seed.js + ?v= + sw 캐시
    sources = json.loads((BASE / 'data' / 'source-videos.seed.json').read_text(encoding='utf-8'))
    payload = {'songs': songs, 'sources': sources, 'meta': meta}
    (BASE / 'src' / 'seed.js').write_text(
        'window.STRUM_SEED = ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')
    for name in ('index.html', 'src/app.js', 'src/styles.css'):
        p = BASE / name
        p.write_text(re.sub(r'\?v=\d+', f'?v={SEED_VERSION}', p.read_text(encoding='utf-8')), encoding='utf-8')
    sw = BASE / 'sw.js'
    t = sw.read_text(encoding='utf-8')
    t = re.sub(r"var CACHE = 'strum-busking-test-v\d+';", f"var CACHE = 'strum-busking-test-v{SEED_VERSION}';", t)
    sw.write_text(t, encoding='utf-8')

    # 요약
    male_key = [sid for sid in MR]
    kept = list(KEEP_ANNOTATE)
    print(f'OK · seedVersion {SEED_VERSION}')
    print(f'   MR 남자키 교체 {len(male_key)}개 항목 / 서로 다른 영상 {len(set(v for v, _ in MR.values()))}개')
    print(f'   기존 유지+원키 표시 {len(kept)}개 항목: {", ".join(kept)}')
    print(f'   음악 영상 남자 커버 교체 {len(VIDEO)}개 항목')


if __name__ == '__main__':
    main()
