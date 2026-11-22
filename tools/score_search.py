#!/usr/bin/env python3
"""코드스코어(chordscore) 공개 API에서 곡 정보(원키·박자·BPM)와 공개 미리보기 마디를 모은다.

- 검색: https://api.chordscore.com/api/search/index?keyword=
- 상세: https://api.chordscore.com/api/score/detail?id=  (로그인 없이 공개되는 앞부분만)
결과는 tmp/score/<slug>.json 에 저장한다. 값은 검수 전 원문이다.
"""
import json
import pathlib
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

BASE = pathlib.Path(__file__).resolve().parents[1]
OUT = BASE / 'tmp' / 'score'
API = 'https://api.chordscore.com/api'
HEAD = {'User-Agent': 'Mozilla/5.0', 'Origin': 'https://chordscore.com', 'Referer': 'https://chordscore.com/'}


def get(url):
    req = urllib.request.Request(url, headers=HEAD)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode('utf-8', 'ignore'))


def norm(s):
    s = unicodedata.normalize('NFKC', str(s)).lower()
    return re.sub(r'[^0-9a-z가-힣ぁ-ゖァ-ヺ一-龥]+', '', s)


def search(keyword):
    d = get(f'{API}/search/index?keyword=' + urllib.parse.quote(keyword))
    mus = d.get('data', {}).get('musics', {})
    return mus.get('data', []) if isinstance(mus, dict) else []


def detail(sid):
    d = get(f'{API}/score/detail?id={sid}')
    return d.get('data', {})


def bars_of(data):
    out = []
    for m in data.get('musics', []):
        slots = [m.get(f'chord_{i}') or '' for i in range(1, 17)]
        out.append({'sort': m.get('sort'), 'slots': slots})
    return out


def strip_tags(s):
    return re.sub(r'<[^>]+>', '', s or '')


def main():
    works = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
    OUT.mkdir(parents=True, exist_ok=True)
    for w in works:
        slug = w['slug']
        rec = {'work': w}
        try:
            cands = search(f"{w['title']} {w.get('artist','')}".strip())
            rec['candidates'] = [{'id': c['id'], 'title': c['title'], 'singer': c.get('singer')} for c in cands[:8]]
            pick = None
            for c in cands:
                if norm(w['title']) in norm(c['title']) and (not w.get('artist') or norm(w['artist'])[:3] in norm(c.get('singer')) or norm(c.get('singer'))[:3] in norm(w['artist'])):
                    pick = c
                    break
            if not pick:
                for c in cands:
                    if norm(w['title']) in norm(c['title']):
                        pick = c
                        break
            if pick:
                rec['picked'] = pick
                d = detail(pick['id'])
                rec['info'] = d.get('info')
                rec['bars'] = bars_of(d)
        except Exception as e:  # noqa: BLE001
            rec['error'] = str(e)
        (OUT / f'{slug}.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
        info = rec.get('info') or {}
        print(f"[{slug}] {info.get('title','(없음)')} / {info.get('singer','')} | key={info.get('original_key')} {info.get('beat')} {info.get('tempo')}bpm | 후보 {len(rec.get('candidates',[]))}")
        if rec.get('bars'):
            for b in rec['bars']:
                s = ' '.join(x for x in b['slots'] if x)
                print('   bar', b['sort'], ':', strip_tags(s)[:120])
        elif rec.get('candidates'):
            print('   cands:', [(c['title'], c['singer']) for c in rec['candidates'][:4]])


if __name__ == '__main__':
    main()
