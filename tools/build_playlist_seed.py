#!/usr/bin/env python3
"""재생목록 확인 기록(docs CSV)을 앱 시드 데이터로 반영한다.

- 원본 25곡(+추천 1곡)의 id/sourceIndices/verification 등 기존 값을 보존한다.
- 공개 168개 영상: 확인된 URL/제목/채널을 슬롯에 넣고, 기존 25곡에 없는 영상은 곡으로 추가한다.
- 접근 불가 42개: 가짜 URL 없이 사유를 남기고, 복원/사용자 확인 19곡은 곡으로 추가한다.
- #163 제외, #6 7곡, #65 2곡, #172 가수 미확인은 유지한다.

실행: python3 tools/build_playlist_seed.py
"""
import csv, json, pathlib, re

BASE = pathlib.Path(__file__).resolve().parents[1]
PLAYLIST = BASE / 'docs' / '재생목록_현재목록_2026-11-22.csv'
DETAIL = BASE / 'docs' / '재생목록_42개_상세_2026-11-22.csv'

USER_CONFIRMED = {
    96: ('And July', '헤이즈 (Heize)'),
    201: ('HER', '블락비 (Block B)'),
}

# 아카이브 복원 17곡: 슬롯 -> (곡명, 원곡 가수, 전체 아카이브 제목)
ARCHIVE = {
    93: ('無題 (무제)', '지드래곤 (G-DRAGON)',
         '도경수 (D.O.) "無題 (무제)" AI Remix | Org. G-DRAGON 지드래곤'),
    100: ('Good Bye-Bye (グッバイバイ)', 'Tomioka Ai',
          '도경수 (D.O.) "Good Bye-Bye(グッバイバイ)" AI Remix | Org. Tomioka Ai'),
    102: ('눈이 오잖아 (When it snows)', '이무진 X 헤이즈',
          '백현 X 도경수 (BAEKHYUN X D.O.) "눈이 오잖아 (When it snows)" | Org. 이무진 X 헤이즈 LEE MUJIN X HEIZE'),
    119: ('비도 오고 그래서 (You, Clouds, Rain)', '헤이즈 (HEIZE)',
          '도경수 X 원필 D.O. X WONPIL "비도 오고 그래서 (You, Clouds, Rain)" ai remix by 헤이즈 HEIZE'),
    122: ('Vancouver', 'BIG Naughty (서동현)',
          '도경수 (D.O.) "Vancouver" [AI REMIX By BIG Naughty 서동현]'),
    123: ('안아줘 (hug me)', '정준일 (Jung Joonil)',
          '도경수 (D.O.) "안아줘 (hug me)" [AI REMIX By 정준일 Jung Joonil]'),
    125: ('미안해 미워해 사랑해 (Love You With All My Heart)', '크러쉬 (CRUSH)',
          '도경수 (D.O.) "미안해 미워해 사랑해 (Love You With All My Heart)" AI Remix | Org. 크러쉬 CRUSH'),
    128: ('어떻게 이별까지 사랑하겠어, 널 사랑하는 거지', '원곡 가수 미확인',
          "도경수 D.O. \"어떻게 이별까지 사랑하겠어, 널 사랑하는 거지 (How can I love the heartbreak, you're the one I love)\" ai remix"),
    130: ('첫눈처럼 너에게 가겠다 (I will go to you like the first snow)', '에일리 (AILEE)',
          '도경수 (D.O.) "첫눈처럼 너에게 가겠다 (I will go to you like the first snow)" AI Remix | Org. 에일리 AILEE'),
    131: ('0+0', '한로로 (HANRORO)',
          '도경수 (D.O.) "0+0" AI Remix | Org. 한로로 HANRORO'),
    132: ('사랑하게 될 거야', '한로로',
          '도경수 (D.O.) "사랑하게 될 거야" AI Remix | Orig. 한로로'),
    140: ('예뻤어 (You were beautiful)', '데이식스 DAY6',
          '도경수 (D.O.) "예뻤어 (You were beautiful)" AI Remix | Org. 데이식스 DAY6'),
    142: ('청혼하지 않을 이유를 못 찾았어 (Propose)', '이무진 (LEE MUJIN)',
          '도경수 (D.O.) "청혼하지 않을 이유를 못 찾았어 (Propose)" AI Remix | Org. 이무진 LEE MUJIN'),
    144: ('기억을 걷는 시간 (Time Spent Walking Through Memories)', '넬 (NELL)',
          '도경수 X 영케이 D.O. X YOUNG K "기억을 걷는 시간 (Time Spent Walking Through Memories)" ai remix by 넬 NELL'),
    146: ('Way Back Home', 'Shaun',
          '백현 X 도경수 (BAEKHYUN X D.O.) "Way Back Home" AI REMIX | Org. Shaun'),
    150: ('WHAT IS LOVE (2026.ver)', 'EXO-K',
          '백현 X 도경수 (BAEKHYUN X D.O.) "WHAT IS LOVE (2026.ver)" [AI REMIX By EXO-K]'),
    151: ('Lonely', '2NE1',
          '백현 X 도경수 (BAEKHYUN X D.O.) "Lonely" [AI REMIX By 2NE1]'),
}

# 기존 25곡: 확인된 공개 영상 슬롯과 근거 메모
MATCHED = {
    'verified-001': (21, '공개 영상(원곡)', '공개 영상 확인(2026-11-22): 재생목록 #21 「음원차트 역주행 신화, 감성 보컬 오왠의 자작곡 ‘오늘’」 (RE2AgFBJ80E).'),
    'verified-002': (105, '공개 영상(커버)', '공개 영상 확인(2026-11-22): 재생목록 #105 「우효(OOHYO) - 민들레 (Cover by 하현상 Ha Hyunsang)」 (Qw48FXivjYY). 원곡자가 아닌 커버 영상.'),
    'verified-003': (28, '공개 영상(커버)', '공개 영상 확인(2026-11-22): 재생목록 #28 「Dido - Thank You 남자커버」 (1QmhbcZPZZE).'),
    'verified-014': (65, '공개 영상(커버)', '공개 영상 확인(2026-11-22): 재생목록 #65 「사별 死別」 (8PCQyS6BBmg).'),
    'verified-016': (74, '공개 영상(커버)', '공개 영상 확인(2026-11-22): 재생목록 #74 「how to cry 커버」 (YRwLtKsgvW4).'),
    'verified-017': (108, '공개 영상(원곡)', '공개 영상 확인(2026-11-22): 재생목록 #108 아소 - 나는 버려질 장난감 (YJdyPtShNvE).'),
    'verified-018': (109, '공개 영상(커버)', '공개 영상 확인(2026-11-22): 재생목록 #109 YOASOBI - 아마도 cover (dvywQM3UqGM).'),
    'verified-021': (171, '공개 영상(원곡)', '공개 영상 확인(2026-11-22): 재생목록 #171 「날씨가좋고 바람도 좋아2」 (ctwIj615b18) — 기존 원본 번호 #172와 1 차이. 가수는 여전히 미확인.'),
    'verified-024': (202, '공개 영상(원곡)', "공개 영상 확인(2026-11-22): 재생목록 #202 「X에서 난리 난 엑디즈 주연 '닮은 사람' 라이브 #이기찬 #주연」 (JIEuvqny0yc) — 기존 원본 번호 #203과 1 차이."),
}
EXTRA_INDICES = {
    'verified-001': [21],
    'verified-002': [105],
    'verified-003': [28],
    'verified-021': [171, 172],
    'verified-024': [202, 203],
}
MISMATCH_NOTES = {
    'verified-004': '원본 #2 슬롯의 현재 재생목록 영상은 「나보다 못부르네」(KcTFE8g7UN8)이며 Ten Thousand Hours 영상으로 확인되지 않아 연결하지 않음.',
    'verified-005': '원본 #6 묶음 영상은 현재 재생목록에서 이 곡으로 확인되지 않아 영상 링크를 연결하지 않음.',
    'verified-006': '원본 #6 묶음 영상은 현재 재생목록에서 이 곡으로 확인되지 않아 영상 링크를 연결하지 않음.',
    'verified-007': '원본 #6 묶음 영상은 현재 재생목록에서 이 곡으로 확인되지 않아 영상 링크를 연결하지 않음.',
    'verified-008': '원본 #6 묶음 영상은 현재 재생목록에서 이 곡으로 확인되지 않아 영상 링크를 연결하지 않음.',
    'verified-009': '원본 #6 묶음 영상은 현재 재생목록에서 이 곡으로 확인되지 않아 영상 링크를 연결하지 않음.',
    'verified-010': '원본 #6 묶음 영상은 현재 재생목록에서 이 곡으로 확인되지 않아 영상 링크를 연결하지 않음.',
    'verified-011': '원본 #6 묶음 영상은 현재 재생목록에서 이 곡으로 확인되지 않아 영상 링크를 연결하지 않음.',
    'verified-012': '원본 #20 슬롯의 현재 영상은 혁오 곡 커버(카더가든, QYxrJAkD81c)로 TOMBOY 영상인지 확인되지 않아 연결하지 않음.',
    'verified-013': '원본 #65 슬롯의 현재 영상은 死別(8PCQyS6BBmg)이며 Flower 영상으로 확인되지 않음. #29는 로이킴이 부른 Flower 커버(Fn9tOOYXXKs)로 원본 영상이 아님.',
    'verified-015': '원본 #70 슬롯의 현재 영상은 「매너가 사람을 만든다ㄷㄷ」(tr2rrgupEzM)로 Englishman in New York 영상으로 확인되지 않음.',
    'verified-019': '원본 #165 슬롯의 현재 영상은 「내 손을 잡아 레전드 파트…」로 이 곡이 아님. 관련 영상은 #170·#174(박진영 파트)뿐이며 원곡 영상은 확인되지 않음.',
    'verified-020': '원본 #169 슬롯의 현재 영상은 소수빈 - 더 아름다워져(UAfwlN2__kc)로 오르막길 영상이 아님.',
    'verified-022': '원본 #197 슬롯의 현재 영상은 유영우 숏츠(Uq56vKHRXQI)로 이 곡 영상이 아님.',
    'verified-023': '원본 #201 슬롯은 사용자 확인 결과 블락비 - HER 곡으로 밝혀짐. 이 곡(소란)과 같은 번호에 있는 번호 대응 불일치로, 기존 기록을 보존한 채 둘 다 유지. 영상은 재생 불가(업로더 삭제).',
    'verified-025': '현재 재생목록은 210개 항목까지이며 #211 영상은 확인되지 않음. 영상 링크 없음.',
}

REASON_ORDER = ('계정 해지', '비공개', '저작권 삭제', '업로더 삭제')


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def watch(vid):
    return f'https://www.youtube.com/watch?v={vid}'


def reason_key(text):
    for key in REASON_ORDER:
        if key in text:
            return key
    return ''


def main():
    rows = {int(r['순번']): r for r in read_csv(PLAYLIST)}
    detail = {int(r['순번']): r for r in read_csv(DETAIL)}
    assert len(rows) == 210 and len(detail) == 42

    songs = json.loads((BASE / 'data' / 'songs.seed.json').read_text(encoding='utf-8'))
    sources = {s['index']: s for s in json.loads((BASE / 'data' / 'source-videos.seed.json').read_text(encoding='utf-8'))}
    songs_by_id = {s['id']: s for s in songs}

    def upsert(rec):
        for i, cur in enumerate(songs):
            if cur['id'] == rec['id']:
                songs[i] = rec
                return
        songs.append(rec)

    def append_note(s, text):
        s['notes'] = (s['notes'].strip() + ' ' if s.get('notes', '').strip() else '') + text

    # 1) 기존 25곡: 확인된 영상만 연결하고 나머지는 근거 메모만 남긴다.
    for sid, rec in songs_by_id.items():
        if sid.startswith('verified-'):
            rec.setdefault('videoStatus', '영상 미확인')
            if sid in MATCHED:
                slot, status, note = MATCHED[sid]
                rec['videoUrl'] = watch(rows[slot]['영상ID'])
                rec['videoStatus'] = status
                rec['sourceIndices'] = EXTRA_INDICES.get(sid, rec['sourceIndices'])
                if note[:30] not in rec.get('notes', ''):
                    append_note(rec, note)
            elif sid in MISMATCH_NOTES:
                if MISMATCH_NOTES[sid][:30] not in rec.get('notes', ''):
                    append_note(rec, MISMATCH_NOTES[sid])
        elif sid == 'suggested-stand-by-me':
            rec.setdefault('videoStatus', '')

    # 2) 공개 168개 슬롯 + 접근 불가 42개 슬롯 + #211
    for i in range(1, 212):
        sources[i].setdefault('title', '')
        sources[i].setdefault('channel', '')
        sources[i].setdefault('reason', '')
    public_count = inaccessible = 0
    for idx in range(1, 211):
        row = rows[idx]
        src = sources[idx]
        src['title'] = row['제목'] if row['상태'] == '표시됨' else ''
        src['channel'] = row['채널·조회수'].split(' · ')[0].strip() if row['상태'] == '표시됨' else ''
        src['reason'] = ''
        if row['상태'] == '표시됨':
            public_count += 1
            if idx == 163:
                src['status'] = '제외'
                src['url'] = watch(row['영상ID'])
                src['note'] = f'선별 목록에서 제외 유지(이전 요청). 현재 재생목록 #{idx} 공개 영상: 「{row["제목"]}」({row["영상ID"]}). 곡 라이브러리에는 추가하지 않음.'
            else:
                src['status'] = '확인'
                src['url'] = watch(row['영상ID'])
                src['note'] = f'공개 영상 · {row["영상ID"]}'
        else:
            inaccessible += 1
            src['status'] = '접근 불가'
            src['url'] = ''
            src['reason'] = reason_key(detail[idx]['상태사유'])
            src['note'] = f'영상 불가({src["reason"]}) · 영상 ID {row["영상ID"]} · 재생 URL 등록 안 함(가짜 링크 금지)'

    # #6 / #65 / #163 / #211 기존 의미 보존 메모
    sources[6]['note'] = ('현재 재생목록 #6 공개 영상은 「' + rows[6]['제목'] + '」(' + rows[6]['영상ID'] + ')이지만, '
                          '기존에 #6으로 묶여 있던 7곡(추억이면·희재·한숨·내가 너의 곁에 잠시 살았다는 걸·예뻤어·도망가자·청혼)의 영상인지는 확인되지 않음. 7곡은 각각 독립 유지.')
    sources[65]['note'] = ('현재 재생목록 #65 공개 영상은 「' + rows[65]['제목'] + '」(' + rows[65]['영상ID'] + ')이며 死別 곡과 일치. '
                           '기존에 #65로 묶여 있던 2곡(Flower·死別)은 각각 독립 유지.')
    sources[163]['note'] = ('선별 목록에서 제외 유지(이전 요청). 현재 재생목록 #163 공개 영상은 「' + rows[163]['제목'] + '」(' + rows[163]['영상ID'] + ')이지만 곡 라이브러리에는 추가하지 않음.')
    sources[211]['note'] = '현재 재생목록은 210개 항목까지(1차 기록 211개와 1개 차이). #211 히로인 곡 슬롯은 유지하되 영상은 미확인.'
    sources[17]['note'] = ('공개 영상 · ' + rows[17]['영상ID'] + ' · 「' + rows[17]['제목'] + '」. '
                           '사용자 확인 #96(헤이즈 - And July) 곡의 공개 커버 영상으로 함께 연결.')
    sources[201]['note'] = ('영상 불가(업로더 삭제) · 영상 ID ' + rows[201]['영상ID'] + '. '
                            '사용자 확인 결과 이 번호의 곡은 블락비 - HER. 기존 기록의 소란 - 사랑한 마음엔 죄가 없다도 같은 #201에 연결되어 있어 번호 대응이 충돌하지만 둘 다 보존.')
    # 기존 곡과 현재 영상이 같은 번호에 있으나 대응이 확인되지 않은 슬롯
    for idx in (2, 6, 20, 70, 165, 169, 172, 197, 203):
        if sources[idx]['status'] == '확인':
            sources[idx]['note'] += ' · 기존 기록의 곡도 이 번호에 연결되어 있으나 영상 대응은 확인되지 않음(번호 대응 규칙 미확정).'

    # 2-1) 접근 불가 슬롯에 복원 곡명/미복원 사유를 함께 남긴다.
    for idx in range(1, 211):
        if sources[idx]['status'] != '접근 불가':
            continue
        if idx in USER_CONFIRMED:
            title, artist = USER_CONFIRMED[idx]
            sources[idx]['note'] += f' · 복원된 곡(사용자 확인): {artist} - {title}'
        elif idx in ARCHIVE:
            title, artist, _full = ARCHIVE[idx]
            sources[idx]['note'] += f' · 복원된 곡(아카이브): {artist} - {title}'
        else:
            sources[idx]['note'] += ' · 곡명 미복원(공개 출처로 확인 불가)'

    # 3) 공개 영상 중 기존 25곡에 없는 것 → 곡 추가
    #    같은 영상이 두 번 들어간 198/199, 208/209는 한 곡에 두 슬롯을 연결한다.
    matched_slots = {slot for slot, _, _ in MATCHED.values()}
    duplicate_of = {199: 198, 209: 208}
    # #17은 사용자 확인 #96(헤이즈 - And July) 곡의 공개 영상으로 함께 연결한다.
    absorbed = {17}
    added_raw = 0
    for idx in range(1, 211):
        if rows[idx]['상태'] != '표시됨':
            continue
        if idx == 163 or idx in matched_slots or idx in absorbed:
            continue
        primary = duplicate_of.get(idx, idx)
        if idx in duplicate_of:
            continue
        row = rows[primary]
        channel = row['채널·조회수'].split(' · ')[0].strip()
        sid = f'playlist-{primary:03}'
        if any(s['id'] == sid for s in songs):
            continue
        extra = [duplicate_of_entry for duplicate_of_entry, first in duplicate_of.items() if first == primary]
        upsert({
            'id': sid,
            'title': row['제목'],
            'artist': channel or '미확인',
            'sourceIndices': [primary] + extra,
            'verification': 'playlist-public-video',
            'videoUrl': watch(row['영상ID']),
            'videoStatus': '공개 영상',
            'audioUrl': '',
            'key': '미확정', 'maleKey': '미확정', 'bpm': None,
            'chords': '', 'chordStatus': '미확인', 'strumming': '',
            'difficultyEasy': '미확인', 'difficultyStandard': '미확인', 'vocalDifficulty': '미확인',
            'level': '미착수',
            'tags': ['재생목록 영상', '가수 미확인'],
            'notes': (f'원본 재생목록 #{primary} · 영상 ID {row["영상ID"]} · 채널 {channel} · 유튜브 제목 그대로. '
                      f'가수 필드는 채널명을 표기했으며 원곡 가수·코드·남자 키·BPM은 확인 전이라 비움.'
                      + (f' 같은 영상이 #{idx}에도 중복 포함되어 두 슬롯을 한 곡에 연결.' if extra else '')),
            'setlist': False,
        })
        added_raw += 1

    # 4) 복원/사용자 확인 19곡
    restored = 0
    for idx in sorted(set(ARCHIVE) | set(USER_CONFIRMED)):
        d = detail[idx]
        if idx in USER_CONFIRMED:
            title, artist = USER_CONFIRMED[idx]
            tags = ['사용자 확인', f'원본 #{idx}']
            note = (f'사용자 확인(2026-11-22): {artist} - {title}. 원본 영상은 재생 불가({reason_key(d["상태사유"])}), '
                    f'영상 ID {rows[idx]["영상ID"]}. 가짜 영상 URL은 넣지 않음.')
            if idx == 96:
                tags.append('아카이브 복원')
                note += ' 아카이브된 썸네일에 "And July" 문구가 남아 있었음. 공개 영상 #17(서재민 커버)을 이 곡의 영상으로 함께 연결.'
            if idx == 201:
                note += ' 아카이브(2026-11-05) 썸네일은 유머커리 숏츠였으나, 사용자 확인을 곡 정보의 기준으로 삼음.'
            verification = 'user-confirmed-playlist'
        else:
            title, artist, full = ARCHIVE[idx]
            tags = ['아카이브 복원', 'AI 리믹스', '도경수']
            note = (f'아카이브 복원(2026-11-22): 원 제목 「{full}」 · 채널 EarlGrey(@Earlgrey0820). '
                    f'원본 영상은 재생 불가(계정 해지), 영상 ID {rows[idx]["영상ID"]}. 가짜 영상 URL은 넣지 않음.')
            verification = 'archive-restored'
        sid = f'restored-{idx:03}'
        upsert({
            'id': sid,
            'title': title,
            'artist': artist,
            'sourceIndices': ([17, 96] if idx == 96 else [idx]),
            'verification': verification,
            'videoUrl': (watch(rows[17]['영상ID']) if idx == 96 else ''),
            'videoStatus': ('공개 영상(커버)' if idx == 96 else f'영상 불가({reason_key(d["상태사유"])})'),
            'audioUrl': '',
            'key': '미확정', 'maleKey': '미확정', 'bpm': None,
            'chords': '', 'chordStatus': '미확인', 'strumming': '',
            'difficultyEasy': '미확인', 'difficultyStandard': '미확인', 'vocalDifficulty': '미확인',
            'level': '미착수',
            'tags': tags,
            'notes': note,
            'setlist': False,
        })
        restored += 1

    # 5) 슬롯-곡 연결 재계산
    for s in sources.values():
        s['songs'] = []
    for s in songs:
        for n in s.get('sourceIndices', []):
            if s['id'] not in sources[n]['songs']:
                sources[n]['songs'].append(s['id'])

    # 6) 정렬: 기존 25곡 → 복원/확인 → 공개 영상 → 추천곡
    def rank(s):
        v = s['verification']
        if s['id'].startswith('verified-'):
            return 0
        if v in ('archive-restored', 'user-confirmed-playlist'):
            return 1
        if v == 'playlist-public-video':
            return 2
        return 3
    songs.sort(key=lambda s: (rank(s), s['id']))

    meta = json.loads((BASE / 'data' / 'metadata.json').read_text(encoding='utf-8'))
    meta.update({
        'seedVersion': 3,
        'playlistCollectedCount': 210,
        'playlistPublicVideoCount': public_count,
        'playlistInaccessibleVideoCount': inaccessible,
        'restoredSongCount': restored,
        'songEntryCount': len(songs),
        'sourceDisclosure': ('원본 152곡 전체 데이터는 여전히 미확보. 2026-11-22 확인한 재생목록 210개 항목 중 공개 168개 영상의 제목·URL과 '
                             '접근 불가 42개의 사유·영상 ID를 슬롯에 기록했고, 아카이브 복원 17곡 + 사용자 확인 2곡을 곡으로 추가했다. '
                             '가수·코드·남자 키·BPM은 확인 전 값을 비워 두었다. 211은 원본 영상 번호 슬롯이다.'),
    })

    # 7) 저장
    (BASE / 'data' / 'songs.seed.json').write_text(json.dumps(songs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (BASE / 'data' / 'source-videos.seed.json').write_text(json.dumps([sources[i] for i in range(1, 212)], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (BASE / 'data' / 'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (BASE / 'src' / 'seed.js').write_text('window.STRUM_SEED = ' + json.dumps({'songs': songs, 'sources': [sources[i] for i in range(1, 212)], 'meta': meta}, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')

    cols = ['id', 'title', 'artist', 'sourceIndices', 'verification', 'videoUrl', 'videoStatus', 'audioUrl', 'key', 'maleKey', 'bpm', 'chords', 'chordStatus', 'strumming', 'level', 'tags', 'notes', 'setlist']
    with (BASE / 'data' / 'songs.all.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for s in songs:
            row = {c: s.get(c, '') for c in cols}
            row['sourceIndices'] = '|'.join(map(str, s['sourceIndices']))
            row['tags'] = '|'.join(s['tags'])
            row['setlist'] = str(s['setlist']).lower()
            w.writerow(row)
    with (BASE / 'data' / 'songs.verified.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for s in songs:
            if not s['id'].startswith('verified-'):
                continue
            row = {c: s.get(c, '') for c in cols}
            row['sourceIndices'] = '|'.join(map(str, s['sourceIndices']))
            row['tags'] = '|'.join(s['tags'])
            row['setlist'] = str(s['setlist']).lower()
            w.writerow(row)
    with (BASE / 'data' / 'source-videos.slots.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['index', 'status', 'url', 'title', 'channel', 'reason', 'note', 'songIds'])
        for i in range(1, 212):
            s = sources[i]
            w.writerow([i, s['status'], s['url'], s.get('title', ''), s.get('channel', ''), s.get('reason', ''), s['note'], '|'.join(s['songs'])])

    print(f'songs={len(songs)} public={public_count} inaccessible={inaccessible} restored={restored} raw={added_raw}')
    print('verified', len([s for s in songs if s["id"].startswith("verified-")]), 'suggested', len([s for s in songs if s["verification"].startswith("learning-")]))


if __name__ == '__main__':
    main()
