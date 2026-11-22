#!/usr/bin/env python3
"""STRUM MR(반주) 유튜브 링크 탐색·검증 도구.

- 곡별로 YouTube 검색(inst / MR / 노래방)을 돌려 후보를 모으고,
- 제목에 MR·Inst·노래방·반주 표기가 있는 것만 남긴 뒤,
- YouTube oEmbed(HTTP 200)로 실제 존재와 제목·채널을 확인해 결과 JSON을 만든다.

실행: python3 tools/mr_search.py [--limit N] [--out tmp/mr_result.json]
추측 ID는 만들지 않는다. 검색 결과에 실제로 나온 영상만 후보가 된다.
"""
import argparse
import hashlib
import json
import pathlib
import re
import time
import unicodedata
import urllib.parse
import urllib.request

BASE = pathlib.Path(__file__).resolve().parents[1]
CACHE = BASE / 'tmp' / 'mr_cache'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

# 반주임을 제목에서 확인하는 표기
MARKERS = [
    (r'\(inst\.?\)|\[inst\.?\]|(?<![a-z])inst(?![a-z])', 3),
    (r'(?<![a-z])mr(?![a-z])|m\.\s?r\.?|\[mr\]|\(mr\)|원곡\s*mr', 3),
    (r'tj\s*노래방|tj\s*karaoke', 3),
    (r'금영|geumyoung|keumyoung', 3),
    (r'karaoke', 2),
    (r'노래방', 2),
    (r'반주', 2),
    (r'instrumental', 2),
    (r'カラオケ|インスト|オフボーカル|歌なし', 2),
]
# 반주가 아니라고 판단하는 표기(보컬 커버·라이브·홍보 영상 등)
VETO = [
    r'커버', r'cover', r'라이브', r'\blive\b', r'\bmv\b', r'뮤직비디오', r'가사', r'lyrics?',
    r'teaser', r'티저', r'리액션', r'reaction', r'tutorial', r'레슨', r'강의', r'코드\s*강좌',
    r'악보', r'chord', r'기타\s*강', r'피아노', r'piano', r'코인노래방', r'불러보', r'가창',
    r'모음', r'연속재생', r'playlist', r'shorts', r'쇼츠', r'1시간', r'한시간', r'리믹스', r'remix',
]
GOOD_CHANNEL = [
    (r'- topic$', 3),
    (r'tj노래방|tj karaoke', 5),
    (r'금영', 5),
    (r'원곡노래방', 4),
    (r'진짜\s*반주', 3),
    (r'karaoke|노래방', 2),
]


def norm(s):
    s = unicodedata.normalize('NFKC', str(s or '')).lower()
    return re.sub(r'[\s\(\)\[\]\{\}\.,\'"`·:;!?\-_/\\|&+#%$@~^*+=<>]+', '', s)


def search(query):
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(query.encode()).hexdigest()[:20]
    path = CACHE / f'{key}.html'
    if not path.exists():
        url = 'https://www.youtube.com/results?search_query=' + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            path.write_bytes(r.read())
        time.sleep(0.15)
    html = path.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'var ytInitialData = (\{.*?\});</script>', html, re.S)
    if not m:
        return []
    data = json.loads(m.group(1))
    out = []

    def walk(o):
        if isinstance(o, dict):
            if 'videoRenderer' in o:
                v = o['videoRenderer']
                title = ''.join(x.get('text', '') for x in v.get('title', {}).get('runs', []))
                ch = ''.join(x.get('text', '') for x in v.get('ownerText', {}).get('runs', []))
                dur = v.get('lengthText', {}).get('simpleText', '')
                out.append({'id': v.get('videoId'), 'title': title, 'channel': ch, 'duration': dur})
            else:
                for x in o.values():
                    walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(data)
    return out


def marker_score(title):
    t = str(title or '').lower()
    score, hits = 0, []
    for pat, val in MARKERS:
        if re.search(pat, t, re.I):
            score += val
            hits.append(pat)
    # 원키 그대로인 반주를 우선하고, 키를 옮긴 버전은 감점한다.
    if re.search(r'원키|original key', t, re.I):
        score += 2
    if re.search(r'여자키|남자키|[-+]\s?\d+\s?키|\[\s?[-+]\d+\s?키\s?\]', t, re.I):
        score -= 3
    return score, hits


def vetoed(title):
    t = str(title or '').lower()
    return any(re.search(p, t, re.I) for p in VETO)


def channel_bonus(ch):
    c = str(ch or '').lower()
    bonus = 0
    for pat, val in GOOD_CHANNEL:
        if re.search(pat, c, re.I):
            bonus += val
    return bonus


def judge(work, cand):
    """후보 하나를 점수화. 통과 조건: 반주 표기 + 곡명 일치, 금지 표기 없음."""
    title = cand['title']
    if not cand.get('id') or len(cand['id']) != 11:
        return None
    if vetoed(title):
        return None
    ms, _ = marker_score(title)
    if ms < 2:
        return None
    nt = norm(title)
    ntitle = norm(work['title'])
    nartist = norm(work['artist'])
    title_hit = bool(ntitle) and ntitle in nt
    # 영어/일어 제목이 영상 제목에서 띄어쓰기 없이 붙는 경우는 norm 처리로 이미 흡수
    if not title_hit:
        # 보조 제목(원제)도 확인
        for alt in work.get('altTitles') or []:
            if norm(alt) and norm(alt) in nt:
                title_hit = True
                break
    # TJ·금영 공식 채널도 제목이 '곡명 - 가수' 형식이라 아티스트 표기를 요구한다
    # (같은 제목의 다른 가수 곡을 잘못 붙이지 않기 위해).
    tokens = [t for t in re.split(r'[^0-9a-z가-힣ぁ-んァ-ン]+', str(work['artist']).lower()) if t]
    artist_hit = any((len(t) >= 4 if re.match(r'[0-9a-z]', t) else len(t) >= 2) and t in nt for t in tokens)
    ch = channel_bonus(cand['channel'])
    # 공식 아티스트 Topic 채널의 (Inst.)는 영문 표기라 제목에 한글 가수가 없을 수 있다.
    # 검색어에 가수를 넣어 찾은 경우에만 제한적으로 인정한다.
    official_topic = bool(re.search(r'-\s*topic$', str(cand['channel']), re.I)) and bool(
        re.search(r'\(inst\.?\)|instrumental', title, re.I))
    if not title_hit:
        return None
    if not artist_hit and not (official_topic and norm(nartist[:6]) and str(work['artist']).lower()[:4] in cand.get('query', '').lower()):
        return None
    score = ms * 2 + ch + (5 if title_hit else 0) + (6 if artist_hit else 0)
    if re.search(r'\(inst\.?\)|インスト|instrumental', title, re.I):
        score += 3
    if re.search(r'원곡|official', title, re.I):
        score += 1
    return {'score': score, 'title_hit': title_hit, 'artist_hit': artist_hit,
            'channel_bonus': ch, 'marker': ms}


def oembed(vid):
    url = 'https://www.youtube.com/oembed?url=' + urllib.parse.quote(
        f'https://www.youtube.com/watch?v={vid}', safe='') + '&format=json'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            if r.status != 200:
                return None
            return json.loads(r.read().decode())
    except Exception:
        return None


def find_for_work(work):
    artist = re.sub(r'\([^)]*\)|\[[^\]]*\]', ' ', work['artist']).strip() or work['artist']
    queries = [
        f"{artist} {work['title']} inst",
        f"{work['title']} TJ노래방",
        f"{artist} {work['title']} MR",
        f"{work['title']} 금영노래방",
        f"{work['title']} karaoke",
        f"{work['title']} inst",
        f"{artist} {work['title']} 반주",
    ]
    if re.search(r'[ぁ-んァ-ン]', work['title']):
        queries.insert(1, f"{work['title']} カラオケ")
    best = []
    seen = set()
    for q in queries:
        cands = search(q)
        for c in cands:
            if c['id'] in seen:
                continue
            seen.add(c['id'])
            j = judge(work, c)
            if j:
                best.append({**c, **j, 'query': q})
        if best:
            best.sort(key=lambda x: -x['score'])
            if best[0]['score'] >= 22:
                break
    best.sort(key=lambda x: -x['score'])
    for c in best[:6]:
        meta = oembed(c['id'])
        if not meta:
            continue
        # oEmbed가 돌려준 실제 제목에도 반주 표기가 있어야 한다.
        ms, _ = marker_score(meta.get('title', ''))
        if ms < 2:
            continue
        return {'videoId': c['id'], 'url': f'https://www.youtube.com/watch?v={c["id"]}',
                'title': meta.get('title'), 'channel': meta.get('author_name'),
                'query': c['query'], 'score': c['score'], 'marker': ms}
    return None


def load_works():
    songs = json.loads((BASE / 'data' / 'songs.seed.json').read_text(encoding='utf-8'))
    works, order = {}, []
    for s in songs:
        if s.get('chartStatus') not in ('ready', 'partial', 'original'):
            continue
        title = s.get('workTitle') or s['title']
        artist = s.get('workArtist') or s['artist']
        if not title or not artist or artist in ('가수 미확인',):
            continue
        key = (title, artist)
        if key not in works:
            works[key] = {'title': title, 'artist': artist, 'ids': [], 'altTitles': []}
            order.append(key)
        works[key]['ids'].append(s['id'])
        for alt in (s.get('title'), s.get('workTitle')):
            if alt and alt not in works[key]['altTitles']:
                works[key]['altTitles'].append(alt)
    return [works[k] for k in order]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--out', default='tmp/mr_result.json')
    ap.add_argument('--start', type=int, default=0)
    args = ap.parse_args()
    works = load_works()
    if args.start:
        works = works[args.start:]
    if args.limit:
        works = works[:args.limit]
    out_path = BASE / args.out
    done = {}
    if out_path.exists():
        done = {f"{w['title']}|{w['artist']}": w for w in json.loads(out_path.read_text(encoding='utf-8'))}
    results = list(done.values())
    used = {w['videoId'] for w in done.values() if w.get('videoId')}
    for i, w in enumerate(works, 1):
        key = f"{w['title']}|{w['artist']}"
        if key in done:
            continue
        found = find_for_work(w)
        if found and found['videoId'] in used:
            found = None
        if found:
            used.add(found['videoId'])
        rec = {**w, 'mr': found}
        results.append(rec)
        print(f"[{i}/{len(works)}] {w['title']} — {w['artist']} → "
              f"{(found['title'] + ' / ' + found['channel']) if found else '없음'}", flush=True)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    hit = sum(1 for r in results if r.get('mr'))
    print(f'DONE {hit}/{len(works)} works matched ({len(results)} records)')


if __name__ == '__main__':
    main()
