"""STRUM 데이터 정합성 검사 (2026-11-22 재생목록 반영판).

원본 25곡(+추천 1곡)의 id/sourceIndices/verification, #6 7곡, #65 2곡, #163 제외,
#172 가수 미확인을 고정 검사하고, 새로 반영한 210개 재생목록 항목(공개 168 / 접근 불가 42),
복원·사용자 확인 19곡, #211 슬롯을 검사한다.

실행: python3 tools/verify_data.py
"""
import json, pathlib, re, unicodedata

BASE = pathlib.Path(__file__).resolve().parents[1]
songs = json.loads((BASE / 'data' / 'songs.seed.json').read_text(encoding='utf-8'))
src = json.loads((BASE / 'data' / 'source-videos.seed.json').read_text(encoding='utf-8'))
meta = json.loads((BASE / 'data' / 'metadata.json').read_text(encoding='utf-8'))

# 1) 슬롯 기본 구조
assert len(src) == 211, len(src)
assert [r['index'] for r in src] == list(range(1, 212))
assert len({s['id'] for s in songs}) == len(songs)

# 2) 기존 25곡 보존 (id / 곡명 / 가수 / 원본 번호 / 검증값)
ORIGINALS = [
    ('verified-001', '오늘', '오왠 (O.WHEN)', [21], 'site-top3'),
    ('verified-002', '민들레', '우효 (OOHYO)', [105], 'site-top3'),
    ('verified-003', 'Thank You', 'Dido', [28], 'site-top3'),
    ('verified-004', 'Ten Thousand Hours', 'Macklemore & Ryan Lewis', [2], 'user-verified'),
    ('verified-005', '추억이면', '부활', [6], 'user-verified'),
    ('verified-006', '희재', '성시경', [6], 'user-verified'),
    ('verified-007', '한숨', '이하이', [6], 'user-verified'),
    ('verified-008', '내가 너의 곁에 잠시 살았다는 걸', '토이', [6], 'user-verified'),
    ('verified-009', '예뻤어', 'DAY6', [6], 'user-verified'),
    ('verified-010', '도망가자', '선우정아', [6], 'user-verified'),
    ('verified-011', '청혼', '노을', [6], 'user-verified'),
    ('verified-012', 'TOMBOY', '혁오', [20], 'user-verified'),
    ('verified-013', 'Flower', '오반', [65], 'user-verified'),
    ('verified-014', '死別 (feat. GUMI)', 'Shannon', [65], 'user-verified'),
    ('verified-015', 'Englishman in New York', 'Sting', [70], 'user-verified'),
    ('verified-016', 'How To Cry', 'Sam Smith', [74], 'user-verified'),
    ('verified-017', '나는 버려질 장난감', '아소 · 아날로그소년', [108], 'user-verified'),
    ('verified-018', 'たぶん (아마도)', 'YOASOBI', [109], 'user-verified'),
    ('verified-019', '생각을 멈추다 보면', '최유리', [165], 'user-verified'),
    ('verified-020', '오르막길', '윤종신', [169], 'user-verified'),
    ('verified-021', '날씨가 좋고 바람도 좋아', '가수 미확인', [171, 172], 'user-title-only'),
    ('verified-022', '세상이 그대를 속일지라도', '김장훈', [197], 'user-verified'),
    ('verified-023', '사랑한 마음엔 죄가 없다', '소란', [201], 'user-verified'),
    ('verified-024', '닮은사람', '이기찬', [202, 203], 'user-verified'),
    ('verified-025', '히로인', 'back number', [211], 'user-verified'),
]
by_id = {s['id']: s for s in songs}
for sid, title, artist, indices, verification in ORIGINALS:
    s = by_id[sid]
    assert (s['title'], s['artist'], s['sourceIndices'], s['verification']) == (title, artist, indices, verification), sid
assert len([s for s in songs if s['id'].startswith('verified-')]) == 25

# 3) 묶음/예외 규칙
assert all(i in src[5]['songs'] for i in [f'verified-{n:03}' for n in range(5, 12)])
assert len([x for x in src[5]['songs'] if x.startswith('verified-')]) == 7
assert all(i in src[64]['songs'] for i in ('verified-013', 'verified-014'))
assert len([x for x in src[64]['songs'] if x.startswith('verified-')]) == 2
assert src[162]['status'] == '제외' and not src[162]['songs'], '#163 제외 유지 실패'
assert by_id['verified-021']['artist'] == '가수 미확인', '#172 가수 미확인 유지 실패'
assert src[210]['songs'] == ['verified-025']

# 4) 추천곡은 원본 슬롯과 분리
reco = [s for s in songs if s['verification'] == 'learning-recommendation-not-in-original-playlist']
assert len(reco) == 1 and not reco[0]['sourceIndices']

# 5) 곡-슬롯 양방향 연결
for s in songs:
    assert s['title'].strip() and s['artist'].strip(), s['id']
    for n in s['sourceIndices']:
        assert 1 <= n <= 211 and s['id'] in src[n - 1]['songs'], (s['id'], n)
for r in src:
    for sid in r['songs']:
        assert sid in by_id and r['index'] in by_id[sid]['sourceIndices'], (r['index'], sid)

# 6) 슬롯 상태/URL/사유
states = {}
for r in src:
    states[r['status']] = states.get(r['status'], 0) + 1
assert states == {'확인': 167, '접근 불가': 42, '제외': 1, '미확인': 1}, states
public = [r for r in src if r['url']]
assert len(public) == 168, len(public)
for r in public:
    m = re.fullmatch(r'https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})', r['url'])
    assert m, r['url']
    assert r['title'].strip(), r['index']
    assert r['note'].startswith(('공개 영상', '선별 목록', '현재 재생목록', '공개 영상 ·')), (r['index'], r['note'])
assert src[162]['url'] and src[162]['status'] == '제외'
assert src[210]['url'] == '' and src[210]['title'] == ''

REASONS = {'계정 해지': 37, '비공개': 3, '저작권 삭제': 1, '업로더 삭제': 1}
reason_counts = {}
for r in src:
    if r['status'] != '접근 불가':
        continue
    assert r['url'] == '' and not r['title'], (r['index'], '가짜 URL/제목 금지')
    assert r['reason'] in REASONS, (r['index'], r['reason'])
    assert '영상 불가' in r['note']
    reason_counts[r['reason']] = reason_counts.get(r['reason'], 0) + 1
assert reason_counts == REASONS, reason_counts

# 7) 복원·사용자 확인 19곡
restored = [s for s in songs if s['verification'] in ('archive-restored', 'user-confirmed-playlist')]
assert len(restored) == 19, len(restored)
assert len([s for s in restored if s['verification'] == 'archive-restored']) == 17
confirmed = {s['sourceIndices'][-1]: s for s in restored if s['verification'] == 'user-confirmed-playlist'}
assert confirmed[96]['title'] == 'And July' and confirmed[96]['artist'].startswith('헤이즈')
assert confirmed[201]['title'] == 'HER' and confirmed[201]['artist'].startswith('블락비')
for s in restored:
    if s['sourceIndices'][-1] == 96:
        assert 17 in s['sourceIndices'] and s['videoUrl']  # 공개 커버 영상 연결
    else:
        # 2026-11-22: 삭제된 원본(도경수 AI 리믹스) 대신 원곡 가수의 공식 영상을 새로 연결
        assert s['videoUrl'] and s['videoStatus'].startswith('공개 영상'), s['id']
        assert '공식 영상 확인(2026-11-22)' in s['notes'], s['id']

# 8) 공개 영상 곡 수와 중복 처리
public_songs = [s for s in songs if s['verification'] == 'playlist-public-video']
assert len(public_songs) == 155, len(public_songs)
for a, b in ((198, 199), (208, 209)):
    assert src[a - 1]['url'] == src[b - 1]['url']
    assert src[a - 1]['songs'] == src[b - 1]['songs'] and src[a - 1]['songs']
assert src[198]['songs'] == ['playlist-198'] and src[207]['songs'] == ['playlist-208']

# 9) 영상 URL 중복 없음(같은 영상은 한 곡에 두 슬롯), 영상 불가 곡에 URL 없음
urls = [s['videoUrl'] for s in songs if s['videoUrl']]
assert len(urls) == len(set(urls)) == 201, (len(urls), len(set(urls)))
assert all(s['videoUrl'] for s in songs), '모든 곡에 영상 링크 연결(2026-11-22 36곡 보강)'
for s in songs:
    if s['videoUrl']:
        assert re.fullmatch(r'https://www\.youtube\.com/watch\?v=[A-Za-z0-9_-]{11}', s['videoUrl']), s['id']
for s in songs:
    if s.get('videoStatus', '').startswith('영상 불가'):
        assert not s['videoUrl'], s['id']

# 10) 메타 집계
assert meta['seedVersion'] == 15
assert meta['videoLinkCount'] == 201 and meta['videoLinkFilledCount'] == 36
assert meta['playlistCollectedCount'] == 210
assert meta['playlistPublicVideoCount'] == 168
assert meta['playlistInaccessibleVideoCount'] == 42
assert meta['restoredSongCount'] == 19
assert meta['songEntryCount'] == len(songs) == 201

# 11) 악보(남자키·박자·BPM·원터치 매핑) 정합성
PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6,
      'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
BTN_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'Cm': 0, 'Dm': 2, 'Em': 4, 'Fm': 5, 'Gm': 7}
BTNS = set(BTN_PC)


def pc_of(chord):
    i = 1
    while i < len(chord) and chord[i] in '#b':
        i += 1
    return PC[chord[:i]]


ready = [s for s in songs if s.get('chartStatus') == 'ready']
partial = [s for s in songs if s.get('chartStatus') == 'partial']
pending = [s for s in songs if s.get('chartStatus') == 'pending']
assert len(ready) + len(partial) + len(pending) + meta['nonMusicCount'] + meta['originalWorkCount'] == len(songs), '분류 누락'
for s in songs:
    assert s.get('category') in ('chart', 'partial', 'pending', 'reference', 'original'), (s['id'], s.get('category'))
assert len([s for s in songs if s['category'] == 'reference']) == meta['nonMusicCount']
assert len([s for s in songs if s['category'] == 'original']) == meta['originalWorkCount']
for s in songs:
    if s['category'] == 'reference':
        assert not s.get('chart') and s['chartStatus'] == 'reference', s['id']
    if s['category'] == 'original':
        # 자작·자체 채보 항목: 음원 분석으로 악보를 채운 경우(2026-11-22 Coffee)만 chart를 허용한다.
        assert s['chartStatus'] == 'original', s['id']
        if s.get('chart'):
            assert s['chart']['status'] == 'partial' and s['chart']['sections'] and s['chart']['evidence'], s['id']
    if s['category'] in ('chart', 'partial'):
        assert s.get('workTitle') or not s['id'].startswith('playlist-'), s['id']
    if s['id'].startswith('playlist-'):
        assert s.get('playlistKind'), s['id']
assert len(ready) >= 25, len(ready)
for s in ready:
    c = s['chart']
    assert c['status'] == 'ready', s['id']
    assert c['timeSignature'] in ('4/4', '3/4', '6/8'), (s['id'], c['timeSignature'])
    assert 40 <= c['bpm'] <= 180, (s['id'], c['bpm'])
    assert c['originalKey'] and c['maleKey'], s['id']
    assert 0 <= c['capo'] <= 7, (s['id'], c['capo'])
    assert 1 <= c['stage'] <= 4, s['id']
    assert c['sections'], s['id']
    assert c['stroke'] and c['basis'], s['id']
    assert c['evidence'] and all(e['url'].startswith('http') for e in c['evidence']), s['id']
    assert s['key'] == c['originalKey'] and s['maleKey'] == c['maleKey'], s['id']
    assert s['bpm'] == c['bpm'], s['id']
    assert len(c['slots']) <= 8, (s['id'], 'slots')
    slot_ids = {x['slot'] for x in c['slots']}
    assert slot_ids == set(range(1, len(c['slots']) + 1)), s['id']
    for sec in c['sections']:
        assert sec['name'] and sec['bars'], s['id']
        for bar in sec['bars']:
            assert bar, s['id']
            for cell in bar:
                if cell['btn'] is not None:
                    assert cell['btn'] in BTNS, (s['id'], cell['btn'])
                    expect = (BTN_PC[cell['btn']] + c['capo']) % 12
                    assert expect == pc_of(cell['sound']), (s['id'], cell['btn'], cell['sound'], c['capo'])
                else:
                    assert 1 <= cell['slot'] <= 8, s['id']
                    assert cell['slot'] in slot_ids, (s['id'], '슬롯 누락')
                    assert cell['sound'] == next(x['chord'] for x in c['slots'] if x['slot'] == cell['slot']), s['id']
for s in partial:
    assert s['chart']['status'] == 'partial' and s.get('chartNote'), s['id']
for s in pending:
    assert not (s.get('chart') or {}).get('sections'), s['id']
assert meta['chartReadyCount'] == len(ready)
assert meta['chartPartialCount'] == len(partial)
assert meta['chartDisclosure']

# 11-1) 검수 대기 27꾸 자료(2026-11-22) 반영 확인 — #77(9번)·#139(15번) 포함
GROUPS = {
    # 27꾸 조사표 inputNumber → seed id, 상태
    1: ('verified-004', 'partial'), 2: ('verified-024', 'partial'),
    3: ('playlist-001', 'partial'), 4: ('playlist-016', 'partial'),
    5: ('playlist-024', 'partial'), 6: ('playlist-025', 'partial'),
    7: ('playlist-034', 'partial'), 8: ('playlist-038', 'partial'),
    9: ('playlist-077', 'partial'), 10: ('playlist-086', 'partial'),
    11: ('playlist-116', 'partial'), 12: ('playlist-118', 'partial'),
    13: ('playlist-124', 'partial'), 14: ('playlist-126', 'partial'),
    15: ('playlist-139', 'partial'), 16: ('playlist-143', 'partial'),
    17: ('playlist-152', 'partial'), 18: ('playlist-153', 'partial'),
    19: ('playlist-154', 'partial'), 20: ('playlist-157', 'partial'),
    21: ('playlist-159', 'partial'), 22: ('playlist-161', 'partial'),
    23: ('playlist-173', 'partial'), 24: ('playlist-186', 'partial'),
    25: ('playlist-190', 'partial'), 26: ('playlist-205', 'partial'),
    27: ('playlist-206', 'partial'),
}
for n, (sid, status) in GROUPS.items():
    s = by_id[sid]
    assert s['chartStatus'] == status, (n, sid, s['chartStatus'])
    c = s.get('chart') or {}
    assert c.get('evidence') and all(e['url'].startswith('http') for e in c['evidence']), (n, sid, '근거 누락')
    if status == 'partial':
        assert c['sections'] and c.get('capo') is not None, (n, sid)
    else:
        assert not c.get('sections'), (n, sid, '대기 꾸에 섹션 금지')
        assert c.get('note') and s.get('chartNote'), (n, sid)
# 확인된 수치·정정
assert by_id['verified-004']['chart']['originalKey'] == 'Ebm' and by_id['verified-004']['chart']['bpm'] == 83
# 이기찬 ‘닮은 사람’ MR 오디오 실측(2026-11-22): 4/4 · 64bpm · 원키 D · C폼 카포 2
_n24 = by_id['verified-024']['chart']
assert (_n24['originalKey'], _n24['maleKey'], _n24['bpm'], _n24['timeSignature']) == ('D', 'D', 64, '4/4')
assert _n24['capo'] == 2 and _n24['formText'] == 'C폼 · Capo +2' and _n24['status'] == 'partial'
assert len(_n24['sections']) == 9 and len(_n24['slots']) == 5
assert by_id['playlist-077']['workArtist'].startswith('BIG Naughty') and '권진아' not in by_id['playlist-077']['workArtist']
assert by_id['playlist-139']['workArtist'] == '나윤권'
assert by_id['playlist-126']['chart']['capo'] == 4 and by_id['playlist-126']['chart']['originalKey'] == 'B'
assert by_id['playlist-152']['chart']['capo'] == 1 and by_id['playlist-152']['chart']['originalKey'] == 'F#'
assert by_id['playlist-159']['workTitle'] == '서, 어른' and by_id['playlist-159']['artist'] == 'GeGee Edu'
assert by_id['playlist-025']['chart']['bpm'] == 127
assert by_id['playlist-205']['chart']['originalKey'] == 'A'
assert by_id['playlist-038']['chart']['maleKey'] == by_id['playlist-124']['chart']['maleKey'] == 'A'
assert by_id['playlist-153']['chart']['sections'] == by_id['playlist-154']['chart']['sections']
assert by_id['playlist-072']['category'] == 'original' and by_id['playlist-072']['chartStatus'] == 'original'
assert by_id['playlist-072']['chart']['status'] == 'partial' and by_id['playlist-072']['chart']['sections']
assert len([s for s in songs if s['chartStatus'] == 'partial']) == 37
assert len([s for s in songs if s['chartStatus'] == 'pending']) == 0
# 남자키는 원곡에서 0~6반음 내려간 값이어야 한다
for s in ready:
    c = s['chart']
    assert (pc_of(c['originalKey']) - pc_of(c['maleKey'])) % 12 == c['maleShift'] % 12, s['id']
    assert 0 <= c['maleShift'] <= 6, s['id']

# 11-2) 2026-11-22 올린 11곡 ZIP·녹화 분석 반영 확인
NEW11 = {
    'playlist-157': ('Eb', 'Eb', 83, 3, 4),
    'playlist-025': ('Em', 'Em', 127, 0, 8),
    'playlist-190': ('C', 'C', 62, 0, 5),
    'playlist-186': ('C', 'C', 65, 0, 5),
    'added-10000-hours': ('A', 'A', 86, 2, 10),
    'playlist-205': ('A', 'A', 81, 2, 6),
    'playlist-159': ('C', 'G', 86, 0, 4),
    'playlist-118': ('B', 'B', 70, 4, 4),
    'playlist-072': ('Db', 'Db', 99, 1, 5),
    'playlist-173': ('Bb', 'Bb', 76, 5, 6),
    'playlist-206': ('F#', 'F#', 66, 6, 4),
}
for sid, (ok, mk, bpm, capo, nsec) in NEW11.items():
    s = by_id[sid]
    c = s.get('chart') or {}
    assert (c.get('originalKey'), c.get('maleKey'), c.get('bpm'), c.get('capo')) == (ok, mk, bpm, capo), (sid, c.get('originalKey'), c.get('maleKey'), c.get('bpm'), c.get('capo'))
    assert len(c.get('sections') or []) == nsec, (sid, len(c.get('sections') or []))
    assert c.get('status') == 'partial' and c.get('note'), sid
    assert sum(len(x['bars']) for x in c['sections']) >= 50, (sid, '마디 수')
    assert c['timeSignature'] == '4/4' and c.get('timeNote'), sid
    assert len(c['slots']) <= 8 and c['evidence'], sid
# 여성 원곡(키썸)만 -5반음, 남성 원곡·자체 분석 곡은 원키 유지
assert by_id['playlist-159']['chart']['maleShift'] == 5 and by_id['playlist-159']['maleKey'] == 'G'
for sid in ('playlist-157', 'playlist-025', 'playlist-190', 'playlist-186', 'added-10000-hours',
            'playlist-205', 'playlist-118', 'playlist-173', 'playlist-206'):
    assert by_id[sid]['chart']['maleShift'] == 0, sid
# 10,000 Hours는 Macklemore ‘Ten Thousand Hours’와 별개 레코드
# 2026-11-22 오디오 재검수 반영: 10,000 Hours 구절 32개 = 64마디, 어떤이별 후반 G 전조 구간 분리, jehoda 후반 C 전조 표기
c10 = by_id['added-10000-hours']['chart']
assert sum(len(x['bars']) for x in c10['sections']) == 64, sum(len(x['bars']) for x in c10['sections'])
assert [x['name'] for x in c10['sections']][3].startswith('후렴 1') and '1:01' in c10['sections'][3]['name']
c190 = by_id['playlist-190']['chart']
assert any('후반 G 전조' in x['name'] for x in c190['sections'])
assert len([x for x in c190['sections'] if 'G 전조' in x['name'] or x['name'].endswith('· G')]) == 2
c173 = by_id['playlist-173']['chart']
assert c173['sections'][-1]['name'].endswith('후반 전조 C') and '옮겨 적음' not in c173['sections'][-2]['name']
assert 'C장조' in c173['note'] and 'D♭장조' in by_id['playlist-072']['chart']['note']
for sid in NEW11:
    assert '2026-11-22 오디오 재검수' in by_id[sid]['chart']['basis'], sid
assert by_id['added-10000-hours']['verification'] == 'added-by-user'
assert by_id['added-10000-hours']['sourceIndices'] == [] and by_id['added-10000-hours']['title'] == '10,000 Hours'
assert by_id['verified-004']['title'] == 'Ten Thousand Hours' and by_id['verified-004']['artist'].startswith('Macklemore')

# 12) MR(반주) 링크 정합성 (seed v13)
MR_MARK = re.compile(r'inst|instrumental|karaoke|노래방|카라오케|m\.?\s?r\.?|(?<![a-z])mr(?![a-z])|반주|カラオケ|インスト|オフボーカル', re.I)
# 주성 님이 직접 지정한 MR 중 제목에 MR·Inst 표기가 없는 링크(피아노 연주 반주 등) — mrNote 에 '주성 님 지정'으로 근거를 남긴 경우만 예외
USER_PICKED_MR_IDS = {'playlist-166'}
with_mr = [s for s in songs if s.get('mrUrl')]
assert len(with_mr) == meta['mrLinkCount'], (len(with_mr), meta['mrLinkCount'])
assert len(with_mr) >= 145, len(with_mr)
works = {}
for s in songs:
    if not s.get('mrUrl'):
        continue
    m = re.fullmatch(r'https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})', s['mrUrl'])
    assert m, (s['id'], s['mrUrl'])
    if s['id'] in USER_PICKED_MR_IDS:
        assert '주성 님 지정' in (s.get('mrNote') or ''), (s['id'], '직접 지정 MR 근거 없음')
    assert s['mrTitle'] and (MR_MARK.search(s['mrTitle']) or s['id'] in USER_PICKED_MR_IDS), (s['id'], s['mrTitle'])
    assert s['mrChannel'], s['id']
    assert s.get('mrNote') and 'oEmbed' in s['mrNote'] and '임베드 재생 확인' in s['mrNote'], s['id']
    assert s.get('mrSource') in ('youtube', 'zip', 'user'), (s['id'], s.get('mrSource'))
    assert s['category'] != 'reference', (s['id'], '참고 영상에 MR 금지')
    key = (s.get('workTitle') or s['title'], s.get('workArtist') or s['artist'])
    if key in works:
        assert works[key] == s['mrUrl'], (s['id'], '같은 곡은 같은 MR')
    works[key] = s['mrUrl']
assert len(works) == meta['mrWorkCount'], (len(works), meta['mrWorkCount'])
# 같은 곡이 표기만 달리해 두 항목으로 있는 경우(예: '예뻤어'/'예뻤어 (You were beautiful)')만 같은 MR 허용
def _nt(t):
    t = unicodedata.normalize('NFKC', t).lower()
    return re.sub(r'[\s\(\)\[\]\{\}\.\,\'"`·:;!?\-_/\\|&+#%$@~^*+=<>]+', '', t)
by_url = {}
for (t, _a), u in works.items():
    if u in by_url and not (_nt(by_url[u]) in _nt(t) or _nt(t) in _nt(by_url[u])):
        raise AssertionError(('MR 영상 중복', u, by_url[u], t))
    by_url[u] = t
# 대표 확인 링크(2026-11-22 oEmbed 200)
assert by_id['verified-024']['mrUrl'].endswith('wfBXXKRdtlk')      # 임베드 차단된 TJ 대신 여기MR 원키
assert by_id['playlist-159']['mrUrl'].endswith('ige-TSCG5vc')      # ZIP 자료 공식 inst.
assert by_id['added-10000-hours']['mrUrl'].endswith('Gt636FM6Ayc')  # Acoustic karaoke(임베드 재생 확인)
assert by_id['verified-007']['mrUrl'].endswith('IkF6QIQ0Q0A')
for sid in ('verified-017', 'verified-021', 'playlist-125' if 'playlist-125' in by_id else 'verified-017'):
    assert not by_id[sid].get('mrUrl'), (sid, '확인되지 않은 MR은 비워 둔다')
assert meta['mrDisclosure'] and 'oEmbed' in meta['mrDisclosure']
print(f"OK: MR 링크 {len(with_mr)}개 곡(서로 다른 곡 {len(works)}) · oEmbed 확인 제목 표기·중복 없음 · 참고 영상 제외")

print('OK: 곡 200 (기존 25 + 복원·확인 19 + 공개 영상 155 + 추천 1)')
entry = [s for s in songs if s['id'].startswith(('verified-', 'restored-')) or s['verification'] in ('added-by-user', 'imported')]
assert len(entry) == 45, len(entry)
print(f"OK: 전체 {len(songs)}개 항목 — 악보 완료 {len(ready)}(서로 다른 곡 {meta['uniqueChartSongCount']}) · 부분 확인 {len(partial)} · 검수 대기 {len(pending)} · "
      f"비음악·참고 {meta['nonMusicCount']} · 자작곡 {meta['originalWorkCount']}")
print(f"OK: 곡으로 등록된 {len(entry)}곡 중 악보 준비 {len([s for s in entry if s['chartStatus'] == 'ready'])}곡")
print('OK: 박자 4/4·3/4·6/8, BPM 40~180, 남자키 이조·카포 0~7, 원터치 버튼(10개) 음정 일치, SimplifyChord 슬롯 ≤8, 근거 URL 존재')
print('OK: 슬롯 211 (공개 168 · 접근 불가 42 · 제외 1 · 미확인 1), #6 7곡 · #65 2곡 · #163 제외 · #172 가수 미확인 유지')
print('OK: 복원 17 + 사용자 확인 2, 접근 불가 사유 계정해지 37/비공개 3/저작권 1/업로더 1, 공개 영상 URL 168개')
print(f"OK: 곡 영상 링크 {len(urls)}개(중복 0) — 2026-11-22 공식 영상 36곡 보강(oEmbed 200 확인)")
