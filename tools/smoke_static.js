/** npm-less/static UI sanity test. Run: node tools/smoke_static.js */
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const base = path.join(__dirname, '..');
const songs = JSON.parse(fs.readFileSync(path.join(base, 'data', 'songs.seed.json'), 'utf8'));
const sources = JSON.parse(fs.readFileSync(path.join(base, 'data', 'source-videos.seed.json'), 'utf8'));
const meta = JSON.parse(fs.readFileSync(path.join(base, 'data', 'metadata.json'), 'utf8'));
const curated = songs.filter(s => s.verification !== 'learning-recommendation-not-in-original-playlist').length;
const recommended = songs.length - curated;
const ready = songs.filter(s => s.chartStatus === 'ready').length;
const pending = songs.filter(s => s.chartStatus !== 'ready' && !s.verification.startsWith('learning-')).length;
const appJs = fs.readFileSync(path.join(base, 'src', 'app.js'), 'utf8');
const store = {};

function boot(seedVersion) {
  const root = { innerHTML: '' };
  const created = [];
  const handlers = {};
  const local = seedVersion ? JSON.parse(JSON.stringify(seedVersion)) : null;
  if (local) store['strum-busking-v2'] = JSON.stringify(local);
  const ctx = {
    window: { STRUM_SEED: { songs, sources, meta }, scrollTo() {}, addEventListener() {}, open() {} },
    document: {
      getElementById(id) { return id === 'app' ? root : null; },
      addEventListener(name, fn) { handlers[name] = fn; },
      querySelector() { return null; },
      createElement() { const el = { className: '', id: '', setAttribute() {}, remove() {}, textContent: '', click() {}, style: {}, classList: { add() {}, remove() {} } }; created.push(el); return el; },
      body: { appendChild() {}, classList: { add() {}, remove() {} }, style: {} },
      documentElement: { style: { setProperty() {} } }
    },
    localStorage: { getItem(k) { return store[k] || null; }, setItem(k, v) { store[k] = v; } , removeItem(k){ delete store[k]; } },
    console, Date, Intl, URL, setTimeout, clearTimeout, setInterval, clearInterval, Math, confirm: () => true
  };
  vm.runInNewContext(appJs, ctx);
  return { root, handlers, created };
}
function nav(handlers, name) { handlers.click({ target: { dataset: { nav: name }, closest(q) { return q === '[data-nav]' ? this : null; } }, preventDefault() {} }); }
function act(handlers, cmd) { handlers.click({ target: { dataset: { act: cmd }, closest(q) { return q === '[data-act]' ? this : null; } }, preventDefault() {} }); }

// 1) 신규 브라우저: 첫 화면
let { root, handlers, created } = boot(null);
assert(root.innerHTML.includes('STRUM'));
assert(root.innerHTML.includes(`${ready}곡 준비 완료`), '홈: 준비 완료 곡 수');
assert(root.innerHTML.includes('비음악'), '홈: 분류 요약');
assert(root.innerHTML.includes('성장 로드맵'));

// 2) 곡 라이브러리: 전체 곡 행 + 남자키 배지 + 필터
nav(handlers, 'songs');
assert(root.innerHTML.includes(`<b>${ready}개</b>`), '곡 수 표기');
assert(root.innerHTML.includes('자작·AI곡') && root.innerHTML.includes('비음악·참고'), '분류 필터 칩');
assert((root.innerHTML.match(/class="song-row"/g) || []).length === curated + recommended, '곡 행 수');
assert(root.innerHTML.includes('남자키 <b>'), '남자키 배지');
assert(root.innerHTML.includes('코드 검수 대기') || root.innerHTML.includes('남자키 <b>'), '분류 배지');
assert(root.innerHTML.includes('악보 완료</option>') && root.innerHTML.includes('비음악·참고 영상</option>'), '필터 옵션');
act(handlers, 'filter-cat:reference');
assert((root.innerHTML.match(/비음악·참고 영상/g) || []).length >= meta.nonMusicCount, '비음악 필터 결과');
act(handlers, 'filter-cat:chart-ready');
assert((root.innerHTML.match(/class="song-row"/g) || []).length === ready, '악보 완료 필터 결과');

// 2-1) MR 버튼 + 하단 미니 플레이어
const miniEl = created.find(el => el.id === 'mini-player-root');
assert(miniEl, '미니 플레이어 루트 생성');
nav(handlers, 'songs');
act(handlers, 'filter-cat:all');
assert(root.innerHTML.includes('data-act="mr:verified-001"'), 'MR 버튼(있는 곡)');
assert(root.innerHTML.includes('MR 없음'), 'MR 없음 버튼(없는 곡)');
assert(root.innerHTML.includes('mr-off') && root.innerHTML.includes('mr-on'), 'MR 상태별 표시');
act(handlers, 'filter-cat:chart-ready');
act(handlers, 'mr:verified-001');
assert(miniEl.innerHTML.includes('mini-player'), '미니 플레이어 열림');
assert(miniEl.innerHTML.includes('youtube-nocookie.com/embed/hwZqHCMmjUM'), 'MR 임베드');
assert(miniEl.innerHTML.includes('autoplay=1'), 'autoplay 지원');
assert(miniEl.innerHTML.includes('mini-badge') && miniEl.innerHTML.includes('>MR<'), 'MR 배지');
assert(miniEl.innerHTML.includes('data-act="mini-collapse"') && miniEl.innerHTML.includes('data-act="mini-close"'), '접기·닫기 버튼');
assert(miniEl.innerHTML.includes('id="mini-file"'), '로컬 파일 버튼');
nav(handlers, 'roadmap');
assert(miniEl.innerHTML.includes('mini-frame'), '탭 이동 후에도 유지');
act(handlers, 'chart:verified-007');
assert(miniEl.innerHTML.includes('mini-frame'), '악보 모달 위에서도 유지');
act(handlers, 'mr:verified-007');
assert(miniEl.innerHTML.includes('youtube-nocookie.com/embed/IkF6QIQ0Q0A'), '악보 화면에서 MR 재생');
act(handlers, 'mini-collapse');
assert(handlers.__collapsed !== undefined || miniEl.innerHTML.includes('collapsed'), '접기 상태 반영');
act(handlers, 'mini-close');
assert(miniEl.innerHTML === '', '닫기 후 제거');
// 2-2) MR 음원 파일(주성 님 녹화에서 오디오만 추출) — 미니 플레이어 안 <audio> 재생
act(handlers, 'filter-cat:all');
assert(/data-act="mr:playlist-157"[^>]*>MR</.test(root.innerHTML), 'MR 음원 파일 곡도 MR 버튼');
act(handlers, 'mr:playlist-157');
assert(miniEl.innerHTML.includes('<audio') && miniEl.innerHTML.includes('media/pikpik-mr.mp3'), 'MR 음원 파일 재생(픽픽)');
assert(miniEl.innerHTML.includes('id="mini-audio"') && miniEl.innerHTML.includes('controls') && miniEl.innerHTML.includes('autoplay'), 'MR 음원 컨트롤·자동재생');
assert(!miniEl.innerHTML.includes('iframe'), 'MR 음원은 iframe 없이 재생');
nav(handlers, 'roadmap');
assert(miniEl.innerHTML.includes('mini-audio'), 'MR 음원도 탭 이동 후 유지');
act(handlers, 'chart:playlist-157');
assert(miniEl.innerHTML.includes('mini-audio'), 'MR 음원도 악보 모달 위에서 유지');
act(handlers, 'close');
act(handlers, 'mini-close');
act(handlers, 'mr:playlist-057');
assert(miniEl.innerHTML.includes('youtube-nocookie.com/embed/_aJasCmlQC8'), '잠깐 시간 될까 MR 임베드');
act(handlers, 'mini-close');
// 2-3) AI 보컬 제거 추출 MR 음원 2건(jehoda · 커피) — 미니 플레이어 <audio>
act(handlers, 'filter-cat:all');
for (const [sid, file] of [['playlist-173', 'media/jehoda-mr.mp3'], ['playlist-072', 'media/coffee-mr.mp3']]) {
  assert(new RegExp(`data-act="mr:${sid}"[^>]*>MR<`).test(root.innerHTML), `MR 음원 곡 버튼 ${sid}`);
  act(handlers, `mr:${sid}`);
  assert(miniEl.innerHTML.includes('<audio') && miniEl.innerHTML.includes(file), `MR 음원 재생 ${sid}`);
  assert(miniEl.innerHTML.includes('id="mini-audio"') && !miniEl.innerHTML.includes('iframe'), `MR 음원 <audio> 재생 ${sid}`);
  act(handlers, 'mini-close');
}
act(handlers, 'filter-cat:chart-ready');
act(handlers, 'close');
act(handlers, 'mr:verified-017');
assert(root.innerHTML.includes('MR이 아직 등록되지 않았습니다'), 'MR 없음 안내');
assert(root.innerHTML.includes('name="mrUrl"'), 'URL 붙여넣기 입력');
assert(root.innerHTML.includes('youtube.com/results?search_query='), 'YouTube MR 검색 링크');
act(handlers, 'close');

// 3) 원터치 컬러 악보 모달
nav(handlers, 'songs');
const way=songs.find(x=>x.id==='restored-146').chart;
act(handlers, 'chart:restored-146');
[`Capo ${way.capo}`, way.formButton+'폼', 'Way Back Home', '원터치 악보', 'SimplifyChord', '퍼커시브', '--c:#'].forEach(t => assert(root.innerHTML.includes(t), '악보: ' + t));
assert(/class="cc /.test(root.innerHTML), '마디 카드');
// 4) SimplifyChord 탭 — 슬롯이 없는 곡은 '완주 가능' 안내
act(handlers, 'chart-tab:slots');
assert(root.innerHTML.includes('slot-board') && root.innerHTML.includes('슬롯 없이'), '슬롯 없음 안내');
act(handlers, 'close');
// 4-1) 슬롯이 있는 곡: 5칸 보드 + 세팅 가이드
act(handlers, 'chart:verified-006');
act(handlers, 'chart-tab:slots');
assert(root.innerHTML.includes('이렇게 세팅하세요') && root.innerHTML.includes('S1'), '슬롯 가이드');
assert((root.innerHTML.match(/class="slot /g) || []).length === 5, '슬롯 5칸');
// 5) 스트로크·퍼커시브 탭
act(handlers, 'chart-tab:perc');
assert(root.innerHTML.includes('4단계로 만드는 퍼커시브') && root.innerHTML.includes('STRUM'), '퍼커시브 가이드');
// 6) 근거 탭
act(handlers, 'chart-tab:basis');
assert(root.innerHTML.includes('근거 자료') && root.innerHTML.includes('chordtool.com'), '근거 링크');
assert(root.innerHTML.includes('원곡 키') && root.innerHTML.includes('AeroBand Capo'), '확인한 값');
// 7) 검수 대기 곡은 악보 대신 안내
act(handlers, 'close');
act(handlers, 'chart:verified-011');
assert(root.innerHTML.includes('코드 검수 대기') || root.innerHTML.includes('일부 정보만'), '검수 대기 안내');
act(handlers, 'close');

// 8) 로드맵: 4단계 + 커리큘럼 + 곡 칩
nav(handlers, 'roadmap');
[1, 2, 3, 4].forEach(n => assert(root.innerHTML.includes(`STAGE ${n}`), 'STAGE ' + n));
assert(root.innerHTML.includes('안 질리는 연습 순서'), '커리큘럼');
assert((root.innerHTML.match(/class="song-chip"/g) || []).length > 10, '단계별 곡 칩');
assert(root.innerHTML.includes('퍼커시브 단계 순서'), '퍼커시브 순서');

// 9) 오늘의 연습: 박자 메트로놈 + 원터치 버튼 10개
nav(handlers, 'practice');
assert(root.innerHTML.includes('나의 집중 타이머'));
['4/4', '3/4', '6/8'].forEach(t => assert(root.innerHTML.includes(`data-act="ts:${t}"`), '박자 버튼 ' + t));
assert((root.innerHTML.match(/class="ot-btn"/g) || []).length === 10, '원터치 10버튼');
act(handlers, 'ts:6/8');
assert(root.innerHTML.includes('8분음표 6번'), '6/8 설명');

// 10) 원본 211 + 백업·설정
nav(handlers, 'sources');
assert(root.innerHTML.includes('원본 211개 영상 관리'));
assert(root.innerHTML.includes('접근 불가 <b>42개</b>'), '슬롯 집계');
nav(handlers, 'settings');
assert(root.innerHTML.includes('전체 JSON 백업') && root.innerHTML.includes('악보 설정 CSV'));
assert(root.innerHTML.includes(`${ready}곡`), '설정: 악보 곡 수');

// 11) seedVersion 3 → 5 병합: 기존 연습 기록·숙련도·메모 보존 + 악보 채움
const legacy = {
  version: 2, seedVersion: 12, removedSeedIds: [],
  songs: [{ id: 'verified-001', title: '오늘', artist: '오왠 (O.WHEN)', sourceIndices: [21], verification: 'site-top3', videoUrl: '', audioUrl: '', key: '미확정', maleKey: '미확정', bpm: null, chords: '', chordStatus: '미확인', strumming: '', level: '거의 가능', tags: [], notes: '내가 직접 쓴 메모', setlist: true },
           { id: 'playlist-157', title: '나약함을 고백하는 행위가 가장 강인한 행동 #로꼬 #픽픽 #쇼츠', artist: '올데뮤AllDayMusic', sourceIndices: [157], verification: 'playlist-public-video', videoUrl: '', audioUrl: '', key: 'Eb', maleKey: 'Eb', bpm: 83, chords: '', chordStatus: '부분 확인', strumming: '', level: '연습 중', tags: [], notes: '', setlist: false },
           { id: 'playlist-072', title: '내 첫 자작곡이야ㅎ 제목은 커피', artist: '나의 노래 메모장', sourceIndices: [72], verification: 'playlist-public-video', videoUrl: '', audioUrl: '', key: 'Db', maleKey: 'Db', bpm: 99, chords: '', chordStatus: '자동분석 초안', strumming: '', level: '연습 중', tags: [], notes: '', setlist: false },
           { id: 'playlist-173', title: '괜히 보고 싶은 사실이 조금은 다행인 시간', artist: 'jehoda', sourceIndices: [173], verification: 'playlist-public-video', videoUrl: '', audioUrl: '', key: 'Bb', maleKey: 'Bb', bpm: 76, chords: '', chordStatus: '부분 확인', strumming: '', level: '연습 중', tags: [], notes: '', setlist: false },
           { id: 'verified-007', title: '한숨', artist: '이하이', sourceIndices: [6], verification: 'user-verified', videoUrl: '', audioUrl: '', key: '미확정', maleKey: '미확정', bpm: null, chords: '', chordStatus: '미확인', strumming: '', level: '미착수', tags: [], notes: '', setlist: false, mrUrl: 'https://www.youtube.com/watch?v=PJwPhFGk0pI', mrTitle: '이전 TJ 반주', mrChannel: 'TJ노래방', mrNote: '이전 시드' }],
  sources: Array.from({ length: 211 }, (_, i) => ({ index: i + 1, status: i === 162 ? '제외' : '미확인', url: '', note: '', songs: [] })),
  logs: [{ id: 'log-old-1', date: '2026-11-20', minutes: 33, songId: 'verified-001', mode: 'easy', chords: 'E A', strum: '8비트', memo: '기존 기록' }]
};
({ root, handlers, created } = boot(legacy));
const saved = JSON.parse(store['strum-busking-v2']);
assert(saved.seedVersion === 17, 'seedVersion 17 로 업그레이드');
assert(saved.logs.length === 1 && saved.logs[0].minutes === 33, '기존 연습 기록 보존');
const mine = saved.songs.find(s => s.id === 'verified-001');
assert(mine.level === '거의 가능', '숙련도 보존');
assert(mine.notes === '내가 직접 쓴 메모', '사용자 메모 보존');
assert(mine.setlist === true, '세트리스트 보존');
assert(mine.chart && mine.chart.status === 'ready' && mine.chart.maleShift === 0, '악보 병합(원키 기준 재계산)');
assert(mine.maleKey === 'E' && mine.bpm === 70, '남자키·BPM 병합(남성 원곡 원키 E)');
assert(mine.sourceIndices.includes(21), '원본 번호 유지');
assert(mine.videoUrl === 'https://www.youtube.com/watch?v=RE2AgFBJ80E', '영상 링크 병합(빈 링크 채움)');
assert(saved.sources[162].status === '제외', '#163 제외 유지');
assert(mine.mrUrl === 'https://www.youtube.com/watch?v=hwZqHCMmjUM', 'MR 링크 병합(빈 값만 채움)');
assert(mine.mrTitle && mine.mrChannel, 'MR 제목·채널 병합');
const han = saved.songs.find(s => s.id === 'verified-007');
assert(han.mrUrl === 'https://www.youtube.com/watch?v=IkF6QIQ0Q0A', '임베드 막힌 이전 MR을 재생되는 반주로 교체');
const pik = saved.songs.find(s => s.id === 'playlist-157');
assert(pik.mrAudioUrl === 'media/pikpik-mr.mp3', 'MR 음원 파일 병합');
assert(pik.mrSource === 'user-recording' && pik.mrTitle, 'MR 음원 출처·제목 병합');
assert(pik.level === '연습 중', 'MR 음원 병합 중 숙련도 보존');
for (const [sid, file] of [['playlist-173', 'media/jehoda-mr.mp3'], ['playlist-072', 'media/coffee-mr.mp3']]) {
  const item = saved.songs.find(s => s.id === sid);
  assert(item.mrAudioUrl === file, `MR 음원 병합 ${sid}`);
  assert(item.mrSource === 'user-recording' && /AI 보컬 제거/.test(item.mrNote) && /2026-11-23/.test(item.mrNote), `MR 음원 출처·근거 ${sid}`);
  assert(item.level === '연습 중', `MR 음원 병합 중 숙련도 보존 ${sid}`);
}
const jamkkan = saved.songs.find(s => s.id === 'playlist-057');
assert(jamkkan.mrUrl === 'https://www.youtube.com/watch?v=_aJasCmlQC8', '잠깐 시간 될까 MR 병합');

console.log(`PASS: boot ${songs.length}곡(악보 ${ready}·검수대기 ${pending}), 남자키 배지, 원터치 컬러 악보(5색), SimplifyChord 슬롯, 4단계 로드맵, 4/4·3/4·6/8 메트로놈, 원본 슬롯, 백업, seed v17 병합(기존 기록·숙련도 보존, MR 링크·MR 음원 파일 병합)·MR 버튼·미니 플레이어(임베드·<audio>)`);
