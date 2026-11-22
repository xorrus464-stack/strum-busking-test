#!/usr/bin/env python3
"""여러 곡의 ChordU 코드 페이지를 한 번에 수집해 요약한다(검수 보조).

실행: python3 tools/research_batch.py works.json
입력 JSON: [{"slug": "...", "title": "...", "artist": "..."}]
결과: tmp/research/<slug>.json + 콘솔 요약
"""
import json
import pathlib
import re
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from research_fetch import clean, get, norm, parse_page, search  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parents[1]
OUT = BASE / 'tmp' / 'research'


def main():
    works = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
    OUT.mkdir(parents=True, exist_ok=True)
    for w in works:
        slug = w['slug']
        q = f"{w['title']} {w['artist']}".strip()
        rec = {'query': w}
        try:
            links = search(q)
            picked = None
            for u in links[:8]:
                if norm(w['title']) in norm(urllib.parse.unquote(u)):
                    picked = u
                    break
            if not picked and links:
                picked = links[0]
            rec['candidates'] = [urllib.parse.unquote(u) for u in links[:6]]
            if picked:
                rec['page'] = parse_page('https://chordu.com' + picked)
        except Exception as e:  # noqa: BLE001
            rec['error'] = str(e)
        (OUT / f'{slug}.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
        p = rec.get('page') or {}
        print(f"[{slug}] {p.get('pageTitle','(없음)')} | key={p.get('key')} bpm={p.get('bpm')} capo={p.get('capo')} | {p.get('chordsUsed','')}")
        print('   seq:', (p.get('chordSeq') or rec.get('error', ''))[:260])


if __name__ == '__main__':
    main()
