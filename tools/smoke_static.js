/** npm-less/static UI sanity test. Run: node tools/smoke_static.js */
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const base = path.join(__dirname, '..');
const seed = JSON.parse(fs.readFileSync(path.join(base, 'data', 'songs.seed.json'), 'utf8'));
const sources = JSON.parse(fs.readFileSync(path.join(base, 'data', 'source-videos.seed.json'), 'utf8'));
const meta = JSON.parse(fs.readFileSync(path.join(base, 'data', 'metadata.json'), 'utf8'));
const root={innerHTML:''};
const handlers={};
const store={};
const ctx={window:{STRUM_SEED:{songs:seed,sources,meta},scrollTo(){},addEventListener(){}},document:{getElementById(id){return id==='app'?root:null},addEventListener(name,fn){handlers[name]=fn}},localStorage:{getItem(k){return store[k]||null},setItem(k,v){store[k]=v}},console,Date,Intl,URL,setTimeout,clearTimeout,setInterval,clearInterval,Math,confirm:()=>true};
vm.runInNewContext(fs.readFileSync(path.join(base,'src','app.js'),'utf8'),ctx);
assert(root.innerHTML.includes('STRUM'));
assert(root.innerHTML.includes('25'));
function navigate(name){const btn={dataset:{nav:name},closest(q){return q==='[data-nav]'?this:null}};handlers.click({target:btn,preventDefault(){}});}
navigate('songs');assert(root.innerHTML.includes('25개 곡 항목'));assert((root.innerHTML.match(/class="song-row"/g)||[]).length===26);
navigate('playlist');assert(root.innerHTML.includes(meta.playlistId));assert(root.innerHTML.includes('youtube-nocookie.com/embed/videoseries'));
navigate('practice');assert(root.innerHTML.includes('30분'));assert(root.innerHTML.includes('나의 집중 타이머'));
navigate('sources');assert(root.innerHTML.includes('원본 211개 영상 관리'));
navigate('settings');assert(root.innerHTML.includes('전체 JSON 백업'));
console.log('PASS: boot, 26 song rows, playlist embed, learning, source registry, backup screen');
