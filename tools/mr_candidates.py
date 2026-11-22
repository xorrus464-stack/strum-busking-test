#!/usr/bin/env python3
"""임베드가 막힌 MR을 대체할 후보를 모은다 (TJ노래방 제외).

TJ노래방 공식 채널은 임베드 재생을 막아(플레이어 오류 150) 앱 안에서 틀 수 없다.
그래서 금영(KY)·엠알샵·여기MR·아티스트 공식 inst.·기타 반주 채널 후보를 모아
tools/mr_embed_check.py 로 실제 재생되는 것만 고른다.

출력: tmp/mr_candidates.json  { "<곡명>|<가수>": [{"videoId","title","channel","score"}, ...] }
실행: python3 tools/mr_candidates.py [--limit N]
"""
import argparse
import json
import pathlib
import re
import sys
import unicodedata

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from tools.mr_search import search, marker_score, vetoed, norm  # noqa: E402

GOOD = [
    (r'금영|ky karaoke|ky\.', 8),
    (r'엠알샵|mr shop', 7),
    (r'싱잇|singit', 7),
    (r'여기mr', 6),
    (r'mr\s*노래방|mr karaoke', 6),
    (r'원곡노래방', 6),
    (r'라라노래방|lala karaoke', 5),
    (r'歌っちゃ王|カラオケ', 5),
    (r'- topic$', 4),
    (r'기타치는아빠|guitarpd|라미기타|nee?z guitar|guitar instrumental', 4),
    (r'mirai|ミライカラオケ|edkara', 3),
    (r'karaoke|노래방', 1),
]
BAD = [(r'tj\s*노래방|tj\s*karaoke|tj노래방', 99)]
# 반주가 아니거나 기타 연습에 맞지 않는 영상(보컬 커버·라이브·강의·피아노 반주 등)
VETO = [
    r'커버', r'cover', r'라이브', r'\blive\b', r'챌린지', r'불러보', r'코인노래방',
    r'tutorial', r'레슨', r'강의', r'강좌', r'악보\s*강', r'chord', r'리액션', r'reaction',
    r'피아노', r'piano', r'teaser', r'티저', r'모음', r'연속재생', r'1시간', r'한시간',
    r'shorts', r'쇼츠', r'리믹스', r'remix', r'mr\s*제거',
]


def rank(title, channel, work):
    t, c = str(title).lower(), str(channel).lower()
    if any(re.search(p, t) or re.search(p, c) for p, _ in BAD):
        return -1
    if any(re.search(p, t) for p in VETO):
        return -1
    score, hits = marker_score(title)
    if not hits:
        return -1
    nt = norm(title)
    tokens = [x for x in re.split(r'[^0-9a-z가-힣ぁ-んァ-ン]+', str(work['artist']).lower()) if x]
    artist_hit = any((len(x) >= 4 if re.match(r'[0-9a-z]', x) else len(x) >= 2) and x in nt for x in tokens)
    titles = [work['title']] + (work.get('altTitles') or [])
    title_hit = any(norm(x) and norm(x) in nt for x in titles)
    if not title_hit or not artist_hit:
        # Topic 공식 inst.는 영문 아티스트명이라 제목에 한글 가수가 없을 수 있다
        if not (re.search(r'- topic$', c) and re.search(r'\(inst\.?\)|instrumental', t)):
            return -1
    s = score * 2 + (6 if artist_hit else 0)
    for p, v in GOOD:
        if re.search(p, t) or re.search(p, c):
            s += v
    if re.search(r'원키|original key', t):
        s += 2
    if re.search(r'여자키|남자키|[-+]\s?\d+\s?키|반키', t):
        s -= 7
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    songs = json.loads((BASE / 'data' / 'songs.seed.json').read_text(encoding='utf-8'))
    status = json.loads((BASE / 'tmp' / 'embed_status.json').read_text(encoding='utf-8'))
    works = {}
    for s in songs:
        url = s.get('mrUrl') or ''
        if 'watch?v=' not in url:
            continue
        vid = url.split('watch?v=')[1]
        if status.get(vid) == 'PLAYS':
            continue
        key = (s.get('workTitle') or s['title'], s.get('workArtist') or s['artist'])
        if key not in works:
            works[key] = {'title': key[0], 'artist': key[1], 'altTitles': [s.get('title', '')]}
    out_path = BASE / 'tmp' / 'mr_candidates.json'
    done = json.loads(out_path.read_text(encoding='utf-8')) if out_path.exists() else {}
    items = list(works.items())
    if args.limit:
        items = items[:args.limit]
    for i, (key, work) in enumerate(items, 1):
        k = f'{key[0]}|{key[1]}'
        if k in done and done[k]:
            continue
        artist = re.sub(r'\([^)]*\)|\[[^\]]*\]', ' ', work['artist']).strip() or work['artist']
        queries = [
            f"{work['title']} 금영노래방",
            f"{work['title']} 싱잇 노래방",
            f"{work['title']} MR노래방", 
            f"{work['title']} KY karaoke",
            f"{artist} {work['title']} inst",
            f"{work['title']} 여기MR",
            f"{work['title']} MR",
            f"{work['title']} karaoke",
            f"{artist} {work['title']} 반주",
            f"{work['title']} 엠알샵",
        ]
        if re.search(r'[ぁ-んァ-ン]', work['title']):
            queries.insert(1, f"{work['title']} カラオケ")
        seen, cands = set(), []
        for q in queries:
            for c in search(q):
                if c['id'] in seen:
                    continue
                seen.add(c['id'])
                sc = rank(c['title'], c['channel'], work)
                if sc > 0:
                    cands.append({'videoId': c['id'], 'title': c['title'], 'channel': c['channel'], 'score': sc})
            if len(cands) >= 8:
                break
        cands.sort(key=lambda x: -x['score'])
        done[k] = cands[:8]
        print(f"[{i}/{len(items)}] {key[0]} — {key[1]}: {len(cands[:8])} candidates", flush=True)
        out_path.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding='utf-8')
    print('works with candidates:', sum(1 for v in done.values() if v))


if __name__ == '__main__':
    main()
