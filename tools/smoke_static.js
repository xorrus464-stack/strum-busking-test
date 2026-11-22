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
  const handlers = {};
  const local = seedVersion ? JSON.parse(JSON.stringify(seedVersion)) : null;
  if (local) store['strum-busking-v2'] = JSON.stringify(local);
  const ctx = {
    window: { STRUM_SEED: { songs, sources, meta }, scrollTo() {}, addEventListener() {}, open() {} },
    document: {
      getElementById(id) { return id === 'app' ? root : null; },
      addEventListener(name, fn) { handlers[name] = fn; },
      querySelector() { return null; },
      createElement() { return { className: '', setAttribute() {}, remove() {}, textContent: '', click() {}, style: {} }; },
      body: { appendChild() {} }
    },
    localStorage: { getItem(k) { return store[k] || null; }, setItem(k, v) { store[k] = v; } , removeItem(k){ delete store[k]; } },
    console, Date, Intl, URL, setTimeout, clearTimeout, setInterval, clearInterval, Math, confirm: () => true
  };
  vm.runInNewContext(appJs, ctx);
  return { root, handlers };
}
function nav(handlers, name) { handlers.click({ target: { dataset: { nav: name }, closest(q) { return q === '[data-nav]' ? this : null; } }, preventDefault() {} }); }
function act(handlers, cmd) { handlers.click({ target: { dataset: { act: cmd }, closest(q) { return q === '[data-act]' ? this : null; } }, preventDefault() {} }); }

// 1) 신규 브라우저: 첫 화면
let { root, handlers } = boot(null);
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

// 3) 원터치 컬러 악보 모달
nav(handlers, 'songs');
act(handlers, 'chart:restored-146');
['Capo 1', 'G폼', 'Way Back Home', '원터치 악보', 'SimplifyChord', '퍼커시브', '--c:#'].forEach(t => assert(root.innerHTML.includes(t), '악보: ' + t));
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
  version: 2, seedVersion: 3, removedSeedIds: [],
  songs: [{ id: 'verified-001', title: '오늘', artist: '오왠 (O.WHEN)', sourceIndices: [21], verification: 'site-top3', videoUrl: '', audioUrl: '', key: '미확정', maleKey: '미확정', bpm: null, chords: '', chordStatus: '미확인', strumming: '', level: '거의 가능', tags: [], notes: '내가 직접 쓴 메모', setlist: true }],
  sources: Array.from({ length: 211 }, (_, i) => ({ index: i + 1, status: i === 162 ? '제외' : '미확인', url: '', note: '', songs: [] })),
  logs: [{ id: 'log-old-1', date: '2026-11-20', minutes: 33, songId: 'verified-001', mode: 'easy', chords: 'E A', strum: '8비트', memo: '기존 기록' }]
};
({ root, handlers } = boot(legacy));
const saved = JSON.parse(store['strum-busking-v2']);
assert(saved.seedVersion === 5, 'seedVersion 5 로 업그레이드');
assert(saved.logs.length === 1 && saved.logs[0].minutes === 33, '기존 연습 기록 보존');
const mine = saved.songs.find(s => s.id === 'verified-001');
assert(mine.level === '거의 가능', '숙련도 보존');
assert(mine.notes === '내가 직접 쓴 메모', '사용자 메모 보존');
assert(mine.setlist === true, '세트리스트 보존');
assert(mine.chart && mine.chart.status === 'ready', '악보 병합');
assert(mine.maleKey === 'D' && mine.bpm === 70, '남자키·BPM 병합');
assert(mine.sourceIndices.includes(21), '원본 번호 유지');
assert(saved.sources[162].status === '제외', '#163 제외 유지');

console.log(`PASS: boot ${songs.length}곡(악보 ${ready}·검수대기 ${pending}), 남자키 배지, 원터치 컬러 악보(5색), SimplifyChord 슬롯, 4단계 로드맵, 4/4·3/4·6/8 메트로놈, 원본 슬롯, 백업, seed v4 병합(기존 기록·숙련도 보존)`);
