#!/usr/bin/env python3
"""임베드 재생이 확인된 MR 후보를 골라 tmp/mr_picks.json 에 기록한다.

- tools/mr_embed_check.py 가 쌓은 tmp/embed_status.json(실제 재생 여부)을 사용
- 후보는 tools/mr_candidates.py 가 모은 tmp/mr_candidates.json
- 한 번에 한 라운드씩: 아직 고르지 못한 곡의 다음 후보만 모아 검사 목록을 만든다

실행: python3 tools/mr_pick.py --list tmp/probe_ids.json   # 이번 라운드 검사할 ID 목록
      python3 tools/mr_embed_check.py --ids-file tmp/probe_ids.json
      python3 tools/mr_pick.py --assign                   # 재생되는 후보 배정
"""
import argparse
import json
import pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
CAND = BASE / 'tmp' / 'mr_candidates.json'
STATUS = BASE / 'tmp' / 'embed_status.json'
PICKS = BASE / 'tmp' / 'mr_picks.json'
EXCLUDE = BASE / 'tmp' / 'mr_exclude.json'


def load(p, default):
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', default='')
    ap.add_argument('--assign', action='store_true')
    args = ap.parse_args()
    cands = load(CAND, {})
    status = load(STATUS, {})
    picks = load(PICKS, {})
    exclude = load(EXCLUDE, {})
    if args.list:
        need = []
        for key, list_ in cands.items():
            if key in picks:
                continue
            for c in list_:
                if c['videoId'] in exclude:
                    continue
                if c['videoId'] not in status and c['videoId'] not in need:
                    need.append(c['videoId'])
        pathlib.Path(args.list).write_text(json.dumps(need, ensure_ascii=False, indent=1), encoding='utf-8')
        print('to probe:', len(need), 'assigned:', len(picks))
        return
    if args.assign:
        for key, list_ in cands.items():
            if key in picks:
                continue
            for c in list_:
                if c['videoId'] in exclude:
                    continue
                if status.get(c['videoId']) == 'PLAYS':
                    picks[key] = c
                    break
        PICKS.write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding='utf-8')
        print('picked:', len(picks), '/', len(cands))


if __name__ == '__main__':
    main()
