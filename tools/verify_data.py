"""STRUM 데이터 정합성 검사 (2026-11-22 재생목록 반영판).

원본 25곡(+추천 1곡)의 id/sourceIndices/verification, #6 7곡, #65 2곡, #163 제외,
#172 가수 미확인을 고정 검사하고, 새로 반영한 210개 재생목록 항목(공개 168 / 접근 불가 42),
복원·사용자 확인 19곡, #211 슬롯을 검사한다.

실행: python3 tools/verify_data.py
"""
import json, pathlib, re

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
        assert not s['videoUrl'] and s['videoStatus'].startswith('영상 불가'), s['id']

# 8) 공개 영상 곡 수와 중복 처리
public_songs = [s for s in songs if s['verification'] == 'playlist-public-video']
assert len(public_songs) == 155, len(public_songs)
for a, b in ((198, 199), (208, 209)):
    assert src[a - 1]['url'] == src[b - 1]['url']
    assert src[a - 1]['songs'] == src[b - 1]['songs'] and src[a - 1]['songs']
assert src[198]['songs'] == ['playlist-198'] and src[207]['songs'] == ['playlist-208']

# 9) 영상 URL 중복 없음(같은 영상은 한 곡에 두 슬롯), 영상 불가 곡에 URL 없음
urls = [s['videoUrl'] for s in songs if s['videoUrl']]
assert len(urls) == len(set(urls)) == 165, (len(urls), len(set(urls)))
for s in songs:
    if s['videoUrl']:
        assert re.fullmatch(r'https://www\.youtube\.com/watch\?v=[A-Za-z0-9_-]{11}', s['videoUrl']), s['id']
for s in songs:
    if s.get('videoStatus', '').startswith('영상 불가'):
        assert not s['videoUrl'], s['id']

# 10) 메타 집계
assert meta['seedVersion'] == 4
assert meta['playlistCollectedCount'] == 210
assert meta['playlistPublicVideoCount'] == 168
assert meta['playlistInaccessibleVideoCount'] == 42
assert meta['restoredSongCount'] == 19
assert meta['songEntryCount'] == len(songs) == 200

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
pending = [s for s in songs if s.get('chartStatus') not in ('ready', 'partial')]
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
    assert len(c['slots']) <= 5, (s['id'], 'slots')
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
                    assert 1 <= cell['slot'] <= 5, s['id']
                    assert cell['slot'] in slot_ids, (s['id'], '슬롯 누락')
                    assert cell['sound'] == next(x['chord'] for x in c['slots'] if x['slot'] == cell['slot']), s['id']
for s in partial:
    assert s['chart']['status'] == 'partial' and s.get('chartNote'), s['id']
for s in pending:
    assert not (s.get('chart') or {}).get('sections'), s['id']
assert meta['chartReadyCount'] == len(ready)
assert meta['chartPartialCount'] == len(partial)
assert meta['chartDisclosure']
# 남자키는 원곡에서 0~6반음 내려간 값이어야 한다
for s in ready:
    c = s['chart']
    assert (pc_of(c['originalKey']) - pc_of(c['maleKey'])) % 12 == c['maleShift'] % 12, s['id']
    assert 0 <= c['maleShift'] <= 6, s['id']

print('OK: 곡 200 (기존 25 + 복원·확인 19 + 공개 영상 155 + 추천 1)')
entry = [s for s in songs if s['id'].startswith(('verified-', 'restored-')) or s['verification'] in ('added-by-user', 'imported')]
assert len(entry) == 44, len(entry)
assert len([s for s in entry if s['chartStatus'] == 'ready']) == len(ready)
print(f"OK: 곡으로 등록된 {len(entry)}곡 중 악보 준비 {len(ready)}곡 · 부분 확인 {len(partial)}곡 · 검수 대기 {len(entry) - len(ready) - len(partial)}곡 "
      f"(나머지 {len(songs) - len(entry)}개는 유튜브 영상 제목 항목)")
print('OK: 박자 4/4·3/4·6/8, BPM 40~180, 남자키 이조·카포 0~7, 원터치 버튼(10개) 음정 일치, SimplifyChord 슬롯 ≤5, 근거 URL 존재')
print('OK: 슬롯 211 (공개 168 · 접근 불가 42 · 제외 1 · 미확인 1), #6 7곡 · #65 2곡 · #163 제외 · #172 가수 미확인 유지')
print('OK: 복원 17 + 사용자 확인 2, 접근 불가 사유 계정해지 37/비공개 3/저작권 1/업로더 1, 공개 영상 URL 168개')
