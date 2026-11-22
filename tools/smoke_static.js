/** npm-less/static UI sanity test. Run: node tools/smoke_static.js */
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const base = path.join(__dirname, '..');
const seed = JSON.parse(fs.readFileSync(path.join(base, 'data', 'songs.seed.json'), 'utf8'));
const sources = JSON.parse(fs.readFileSync(path.join(base, 'data', 'source-videos.seed.json'), 'utf8'));
const meta = JSON.parse(fs.readFileSync(path.join(base, 'data', 'metadata.json'), 'utf8'));
const curated = seed.filter(s => s.verification !== 'learning-recommendation-not-in-original-playlist').length;
const recommended = seed.length - curated;
const root = { innerHTML: '' };
const handlers = {};
const store = {};
const ctx = {
  window: { STRUM_SEED: { songs: seed, sources, meta }, scrollTo() {}, addEventListener() {} },
  document: {
    getElementById(id) { return id === 'app' ? root : null; },
    addEventListener(name, fn) { handlers[name] = fn; },
    querySelector() { return null; },
    createElement() { return { className: '', setAttribute() {}, remove() {}, textContent: '' }; },
    body: { appendChild() {} }
  },
  localStorage: { getItem(k) { return store[k] || null; }, setItem(k, v) { store[k] = v; } },
  console, Date, Intl, URL, setTimeout, clearTimeout, setInterval, clearInterval, Math, confirm: () => true
};
vm.runInNewContext(fs.readFileSync(path.join(base, 'src', 'app.js'), 'utf8'), ctx);
assert(root.innerHTML.includes('STRUM'));
assert(root.innerHTML.includes(String(curated)));
function navigate(name) { const btn = { dataset: { nav: name }, closest(q) { return q === '[data-nav]' ? this : null; } }; handlers.click({ target: btn, preventDefault() {} }); }
navigate('songs');
assert(root.innerHTML.includes(`곡 라이브러리는 <b>${curated}개</b>`), '곡 수 표기');
assert((root.innerHTML.match(/class="song-row"/g) || []).length === curated + recommended, '곡 행 수');
assert(root.innerHTML.includes('공개 영상(커버)'), '영상 상태 태그');
assert(root.innerHTML.includes('And July') && root.innerHTML.includes('HER'), '복원/확인 곡 노출');
navigate('playlist');
assert(root.innerHTML.includes(meta.playlistId));
assert(root.innerHTML.includes('youtube-nocookie.com/embed/videoseries'));
assert(root.innerHTML.includes('공개 168'));
navigate('practice');
assert(root.innerHTML.includes('30분'));
assert(root.innerHTML.includes('나의 집중 타이머'));
navigate('sources');
assert(root.innerHTML.includes('원본 211개 영상 관리'));
assert(root.innerHTML.includes('원본 영상 · 제목'));
assert(root.innerHTML.includes('공개 <b>167개</b>') && root.innerHTML.includes('접근 불가 <b>42개</b>'), '슬롯 집계');
navigate('settings');
assert(root.innerHTML.includes('전체 JSON 백업'));
assert(root.innerHTML.includes(`곡 라이브러리 ${curated}개`));
console.log(`PASS: boot, ${curated + recommended} song rows (${curated}+${recommended}), playlist embed, learning, source registry, backup screen`);
