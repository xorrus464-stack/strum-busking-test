#!/usr/bin/env python3
"""ChordU 검색·코드 페이지에서 곡 키/BPM/코드 진행 후보를 수집한다(수동 검수용 보조 도구).

실행: python3 tools/research_fetch.py "곡명" "가수"
결과: tmp/research/<slug>.json  (웹 페이지 원문에서 추출한 값, 검수 전)
"""
import json
import pathlib
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

BASE = pathlib.Path(__file__).resolve().parents[1]
OUT = BASE / 'tmp' / 'research'
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode('utf-8', 'ignore')


def norm(s):
    s = unicodedata.normalize('NFKC', s).lower()
    return re.sub(r'[^0-9a-z가-힣]+', '', s)


def search(q):
    url = 'https://chordu.com/search?q=' + urllib.parse.quote(q)
    h = get(url)
    links = []
    for m in re.finditer(r'href="(/chords-tabs-[^"]+)"', h):
        u = m.group(1)
        if u not in links:
            links.append(u)
    return links


def clean(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)).strip()


def parse_page(url):
    h = get(url)
    desc = ''
    m = re.search(r'<meta name="description" content="([^"]+)"', h)
    if m:
        desc = m.group(1)
    title = ''
    m = re.search(r'<title>(.*?)</title>', h, re.S)
    if m:
        title = clean(m.group(1)).replace('&#x27;', "'")
    key = re.search(r'in song key ([A-G][#b]?m?)(?:,|\s)', desc)
    capo = re.search(r'capo (\d+) fret', desc)
    chord_list = re.search(r'Chords used in .*?: ([^.]+)\.', desc)
    bpm = re.search(r'([\d.]+)<!-- --> bpm', h) or re.search(r'"tempo":([\d.]+)', h)
    # 코드+가사 본문(ChordU 는 코드를 [C] 형태로 끼워 넣는다)
    body = re.sub(r'<script.*?</script>', ' ', h, flags=re.S)
    body = re.sub(r'<style.*?</style>', ' ', body, flags=re.S)
    text = clean(body)
    chorded = ' '.join(re.findall(r'\[[A-G][#b]?[^\]]{0,8}\]', text))
    return {
        'url': 'https://chordu.com' + url,
        'pageTitle': title,
        'description': desc.replace('&#x27;', "'").replace('&amp;', '&'),
        'key': key.group(1) if key else '',
        'capo': int(capo.group(1)) if capo else None,
        'chordsUsed': chord_list.group(1).strip() if chord_list else '',
        'bpm': float(bpm.group(1)) if bpm else None,
        'chordSeq': chorded[:4000],
        'textHead': text[:1200],
    }


def main():
    title, artist = sys.argv[1], sys.argv[2]
    OUT.mkdir(parents=True, exist_ok=True)
    links = search(f'{title} {artist}')
    picked = None
    for u in links[:6]:
        slug = urllib.parse.unquote(u)
        if norm(title) in norm(slug):
            picked = u
            break
    if not picked and links:
        picked = links[0]
    result = {'query': [title, artist], 'candidates': [urllib.parse.unquote(u) for u in links[:8]]}
    if picked:
        try:
            result['page'] = parse_page('https://chordu.com' + picked)
        except Exception as e:  # noqa: BLE001
            result['error'] = str(e)
    slug = re.sub(r'[^0-9a-zA-Z가-힣]+', '-', f'{title}-{artist}').strip('-')[:60]
    (OUT / f'{slug}.json').write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'page'}, ensure_ascii=False))
    if 'page' in result:
        p = result['page']
        print(p['pageTitle'], '| key', p['key'], '| bpm', p['bpm'], '| capo', p['capo'], '|', p['chordsUsed'])
        print(p['chordSeq'][:600])


if __name__ == '__main__':
    main()
