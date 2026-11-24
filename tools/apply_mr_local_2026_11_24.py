#!/usr/bin/env python3
"""주성 님이 올린 화면 녹화 4개를 남자키(-5반음) MP3 반주로 만들어 등록한다 (seed v21, 2026-11-24).

1) 4개 .mp4 에서 오디오만 추출 → 잡음 구간 정리 → rubberband 로 -5반음 피치 시프트(템포·길이 유지)
   → loudnorm(선형, -17 LUFS / TP -1.5 dBTP) → MP3 192kbps 44.1kHz 스테레오
2) media/ 아래 기존 MR 음원과 같은 규칙(user-recording · mrAudioUrl)으로 4곡 6개 항목에 연결
3) 원키 MR 을 가리키던 mrUrl·mrChannel 은 비우고, 출처 유튜브 링크는 mrNote 에 남긴다
4) seedVersion 21 · index.html/app.js/styles.css ?v=21 · sw.js 캐시 v21

검증 기록은 docs/MR_남자키_MP3_2026-11-24.md.

실행: python3 tools/apply_mr_local_2026_11_24.py
"""
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parents[1]
SEED_VERSION = 21
DATE = '2026-11-24'

# 곡 id → (MR 음원 파일, 곡 제목 표기, mrTitle, mrNote)
LOCAL_MR = {
    'verified-014': (
        'media/shannon-sabyeol-mr.mp3',
        'Shannon - 死別 (feat. GUMI) 남자키(-5키) MR (주성 님 녹화)',
        "주성 님 2026-11-24 화면 녹화(유튜브 「死別(사별) | feat. GUMI - シャノン(샤논) 노래방 カラオケ」 · "
        "@LKARAMUSIC · 3분 40초)에서 오디오만 추출 → -5반음 피치 시프트(템포·길이 그대로) · "
        "media/shannon-sabyeol-mr.mp3 (4.9MB) · 미니 플레이어에서 바로 재생, -6~+6반음 실시간 키 조절(2026-11-24)",
    ),
    'verified-019': (
        'media/choiyuri-saenggak-mr.mp3',
        '최유리 - 생각을 멈추다 보면 남자키(-5키) MR (주성 님 녹화)',
        "주성 님 2026-11-24 화면 녹화(유튜브 「생각을 멈추다 보면」 노래방 MR 영상 · 3분 21초)에서 오디오만 추출 → "
        "-5반음 피치 시프트(템포·길이 그대로) · media/choiyuri-saenggak-mr.mp3 (4.5MB) · "
        "미니 플레이어에서 바로 재생, -6~+6반음 실시간 키 조절(2026-11-24)",
    ),
    'playlist-170': (
        'media/choiyuri-saenggak-mr.mp3',
        '최유리 - 생각을 멈추다 보면 남자키(-5키) MR (주성 님 녹화)',
        "주성 님 2026-11-24 화면 녹화(유튜브 「생각을 멈추다 보면」 노래방 MR 영상 · 3분 21초)에서 오디오만 추출 → "
        "-5반음 피치 시프트(템포·길이 그대로) · media/choiyuri-saenggak-mr.mp3 (4.5MB) · "
        "미니 플레이어에서 바로 재생, -6~+6반음 실시간 키 조절(2026-11-24)",
    ),
    'playlist-174': (
        'media/choiyuri-saenggak-mr.mp3',
        '최유리 - 생각을 멈추다 보면 남자키(-5키) MR (주성 님 녹화)',
        "주성 님 2026-11-24 화면 녹화(유튜브 「생각을 멈추다 보면」 노래방 MR 영상 · 3분 21초)에서 오디오만 추출 → "
        "-5반음 피치 시프트(템포·길이 그대로) · media/choiyuri-saenggak-mr.mp3 (4.5MB) · "
        "미니 플레이어에서 바로 재생, -6~+6반음 실시간 키 조절(2026-11-24)",
    ),
    'restored-100': (
        'media/goodbye-bye-mr.mp3',
        'Tomioka Ai - Good Bye-Bye 남자키(-5키) MR (주성 님 녹화)',
        "주성 님 2026-11-24 화면 녹화(유튜브 「[Inst Ver. / MR] Ai Tomioka - Good bye...」 · @rendezvous18.6y6 · "
        "3분 22초)에서 오디오만 추출 → -5반음 피치 시프트(템포·길이 그대로) · media/goodbye-bye-mr.mp3 (4.5MB) · "
        "미니 플레이어에서 바로 재생, -6~+6반음 실시간 키 조절(2026-11-24)",
    ),
    'playlist-159': (
        'media/kisum-seo-eoreun-mr.mp3',
        '키썸 (Kisum) - 서, 어른 남자키(-5키) MR (주성 님 녹화)',
        "주성 님 2026-11-24 틱톡 녹화(@kisumthink 「서, 어른 (inst.)」 · 2분 51초)에서 오디오만 추출 → "
        "-5반음 피치 시프트(템포·길이 그대로) · media/kisum-seo-eoreun-mr.mp3 (3.9MB) · "
        "미니 플레이어에서 바로 재생, -6~+6반음 실시간 키 조절(2026-11-24)",
    ),
}

# 녹화 원본(유튜브·틱톡) 링크 — mrNote 에 함께 남겨 출처를 잃지 않게 한다
SOURCE_VIDEO = {
    'verified-014': 'https://www.youtube.com/watch?v=cLUNCLUE7pk',
    'verified-019': 'https://www.youtube.com/watch?v=Jp4uNTmxiAY',
    'playlist-170': 'https://www.youtube.com/watch?v=Jp4uNTmxiAY',
    'playlist-174': 'https://www.youtube.com/watch?v=Jp4uNTmxiAY',
    'restored-100': 'https://www.youtube.com/watch?v=YVbcUiPMBPM',
    'playlist-159': 'https://www.youtube.com/watch?v=ige-TSCG5vc',
}


def main():
    songs_path = BASE / 'data' / 'songs.seed.json'
    meta_path = BASE / 'data' / 'metadata.json'
    songs = json.loads(songs_path.read_text(encoding='utf-8'))
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    by_id = {s['id']: s for s in songs}

    for sid, (fname, title, note) in LOCAL_MR.items():
        s = by_id[sid]
        assert (BASE / fname).exists(), (fname, 'MR 음원 파일 없음')
        old_mr = s.get('mrUrl') or s.get('mrAudioUrl') or ''
        # 원키 YouTube MR 표시( [원키 MR · -5키 필요] )를 남자키 MP3 반주로 바꾼다
        s.pop('mrUrl', None)
        s.pop('mrChannel', None)
        s.pop('mrEdited', None)
        s['mrAudioUrl'] = fname
        s['mrTitle'] = title
        s['mrNote'] = note + f' · 원본 영상 {SOURCE_VIDEO[sid]}'
        s['mrSource'] = 'user-recording'
        assert '[원키 MR' not in (s.get('mrNote') or '')
        s['notes'] = s['notes'].rstrip() + (
            f' 2026-11-24 남자키 MP3 반주: 주성 님이 올린 화면 녹화에서 오디오만 추출해 '
            f'-5반음(템포 유지)으로 낮춰 {fname} 로 넣었습니다(기존 {old_mr or "MR"} 대체).')

    songs_path.write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # metadata
    meta['seedVersion'] = SEED_VERSION
    meta['mrVersion'] = DATE
    mr_local = len([s for s in songs if s.get('mrAudioUrl')])
    meta['mrAudioFileCount'] = mr_local
    disc = meta.get('mrDisclosure') or ''
    add = ('2026-11-24: 남자키 MR을 찾지 못해 [원키 MR · -5키 필요]로 두었던 4곡 6개 항목'
           '(Shannon 「死別」· 최유리 「생각을 멈추다 보면」 3개 항목 · Tomioka Ai 「Good Bye-Bye」· 키썸 「서, 어른」)은 '
           '주성 님이 올린 화면 녹화에서 오디오만 뽑아 tempo를 유지한 채 -5반음(남자키)으로 낮춘 MP3 반주'
           '(media/ 4개 파일)로 넣었습니다. 미니 플레이어에서 바로 재생되며 -6~+6반음 실시간 키 조절도 됩니다. ')
    if '주성 님이 올린 화면 녹화에서 오디오만 뽑아' not in disc:
        meta['mrDisclosure'] = add + disc
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # seed.js + ?v= + sw 캐시
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

    print(f'OK · seedVersion {SEED_VERSION}')
    print(f'   남자키 MP3 반주 연결 {len(LOCAL_MR)}개 항목 / 서로 다른 파일 {len({v[0] for v in LOCAL_MR.values()})}개')
    print(f'   저장소 MR 음원 파일 총 {mr_local}개 항목')


if __name__ == '__main__':
    main()
