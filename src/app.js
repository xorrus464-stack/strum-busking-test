/* STRUM — no external JavaScript dependencies. Works on static hosts and phones. */
(() => {
  'use strict';
  const seed = window.STRUM_SEED;
  if (!seed) { document.querySelector('#app').textContent = '곡 데이터가 로드되지 않았습니다. src/seed.js를 확인하세요.'; return; }
  const LS = 'strum-busking-v2';
  const LEVELS = ['미착수', '연습 중', '거의 가능', '버스킹 가능'];
  const SOURCE_STATES = ['미확인', '확인', '접근 불가', '제외'];
  const OLD_SEED_NOTES = new Set(['확인된 7곡을 각각 분리 관리','확인된 2곡을 각각 분리 관리','이전 요청에 따라 선별 목록에서 제외']);
  const levels = LEVELS;
  const MODE_OPTIONS = [['easy','원터치 코드 (Easy Chord)'],['standard','정식 코드']];
  /* AeroBand 원터치 버튼 10개 — 앱 화면(2행 5열)과 같은 색 */
  const BTNS = ['C','Dm','Em','F','G','Cm','D','E','Fm','Gm'];
  const BTN_COLOR = {C:'#2f9e6e',Dm:'#2f6df6',Em:'#ea5a35',F:'#a855f7',G:'#3aa8dc',Cm:'#1f7a4d',D:'#1d4fd8',E:'#c9402a',Fm:'#8b34e0',Gm:'#1f8fb5'};
  const STAGES = [
    {n:1, title:'오른손 마스터', sub:'원터치 코드 + 4/4·3/4·6/8 기본 스트로크', color:'#417356'},
    {n:2, title:'코드 전환 & SimplifyChord', sub:'오픈 코드와 바레 코드 5슬롯 매핑', color:'#39718d'},
    {n:3, title:'정식 코드 & 다이내믹', sub:'바레 포함 원코드 · 아르페지오 · 컷', color:'#946e2e'},
    {n:4, title:'퍼커시브 버스킹', sub:'팜뮤트 · 척킹(X) · 바디 타격', color:'#9b5347'}
  ];
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clone = v => JSON.parse(JSON.stringify(v));
  const norm = v => String(v ?? '').trim().toLocaleLowerCase();
  const fmt = n => new Intl.NumberFormat('ko-KR').format(n || 0);
  const dateKey = (d = new Date()) => [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-');
  const mins = n => String(Math.floor(Math.max(0,n) / 60)).padStart(2,'0')+':'+String(Math.max(0,n)%60).padStart(2,'0');
  const get = id => document.getElementById(id);
  const root = get('app');
  const SEED_VERSION = Number(seed.meta.seedVersion || 0);
  const defaultState = () => ({version:2,seedVersion:SEED_VERSION,removedSeedIds:[],songs:clone(seed.songs),sources:clone(seed.sources),logs:[],settings:{mode:'easy',minutes:25,bpm:60,weeklyGoal:5,timeSignature:'4/4',focusSongId:''},selectedRoutine:[],completedStages:[],lastChanged:new Date().toISOString()});
  let state = defaultState(), currentTab='home', modal=null, searchQuery='', statusFilter='all', sourceQuery='', sourceFilter='known', showAllSources=false;
  let trackAudio=null, trackObjectURL=null, metronome=null, bpmTimer=null, practiceInterval=null, remaining=25*60, sessionRunning=false, lastTime=0, toastTimeout=null;
  let seedMerged=false;
  /* 하단 도킹 미니 플레이어 상태 — render()가 #app을 다시 그려도 살아남도록 body에 붙인 별도 루트를 쓴다 */
  let mini=null;
  const miniRoot=(()=>{try{const el=document.createElement('div');el.id='mini-player-root';document.body.appendChild(el);return el;}catch(err){return null;}})();
  try { const saved=JSON.parse(localStorage.getItem(LS)||'null'); if(saved && Array.isArray(saved.songs) && Array.isArray(saved.sources)){ state={...defaultState(),...saved,settings:{...defaultState().settings,...saved.settings}}; state.seedVersion=Number(saved.seedVersion||0); seedMerged=mergeSeed(state); } }
  catch(err) { console.warn('기존 데이터 손상. 복원 파일을 가져오세요.',err); }
  remaining=state.settings.minutes*60;
  const save = () => { state.lastChanged = new Date().toISOString();try {localStorage.setItem(LS,JSON.stringify(state));} catch(e){notice('저장 공간이 가득 찼습니다. 백업 파일을 다운로드하세요.');} };
  function notice(msg) { document.querySelector('.toast')?.remove();let el=document.createElement('div');el.className='toast';el.setAttribute('role','status');el.textContent=msg;document.body.appendChild(el);clearTimeout(toastTimeout);toastTimeout=setTimeout(()=>el.remove(),3500); }
  if(seedMerged){ save(); setTimeout(()=>notice('남자키·박자·원터치 악보 데이터를 반영했습니다. 연습 기록과 숙련도는 그대로입니다.'),350); }
  const song = id => state.songs.find(s=>s.id===id);
  const chartOf = s => (s && s.chart && s.chart.status !== 'pending') ? s.chart : null;
  const orderRank = s => s.verification==='learning-recommendation-not-in-original-playlist' ? 4 : (['archive-restored','user-confirmed-playlist'].includes(s.verification) ? 2 : (s.verification==='playlist-public-video' ? 3 : 1));
  const ordered = () => [...state.songs].sort((a,b)=>orderRank(a)-orderRank(b) || a.title.localeCompare(b.title,'ko'));
  const weekStart = () => {const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate() - ((d.getDay()+6)%7));return d;};
  function weekStats(){const first=weekStart(), end=new Date(first);end.setDate(end.getDate()+7);const ls=state.logs.filter(l=>{const dt=new Date(l.date+'T12:00:00');return dt>=first&&dt<end;});return {ls,days:new Set(ls.map(l=>l.date)).size,total:ls.reduce((s,l)=>s+Number(l.minutes||0),0)};}
  const buskingCount = () => state.songs.filter(s=>s.level==='버스킹 가능').length;
  const songCount = () => state.songs.filter(s=>s.verification!=='learning-recommendation-not-in-original-playlist').length;
  /* 실제 '곡'으로 등록된 항목(사용자 확인 25 + 복원 19 + 직접 추가)과 유튜브 영상 제목 항목을 구분한다 */
  const songEntry = s => /^(verified|restored)-/.test(s.id) || ['added-by-user','imported'].includes(s.verification);
  const chartSongs = () => state.songs.filter(s=>chartOf(s));
  const readySongs = () => state.songs.filter(s=>s.chartStatus==='ready');
  const pendingSongs = () => state.songs.filter(s=>s.category==='pending' || (songEntry(s) && !s.category && s.chartStatus!=='ready' && s.chartStatus!=='partial'));
  const categoryCount = n => state.songs.filter(s=>s.category===n).length;
  const entrySongs = () => state.songs.filter(songEntry);
  const navs = [['home','대시보드'],['songs','곡 라이브러리'],['roadmap','성장 로드맵'],['playlist','유튜브 재생목록'],['practice','오늘의 연습'],['logs','연습 기록'],['sources','211개 원본'],['settings','백업·설정']];
  const action = (cmd,label,klass='btn small') => `<button type="button" class="${klass}" data-act="${cmd}">${label}</button>`;
  const stat = l => `<span class="status" data-level="${esc(l)}">${esc(l)}</span>`;
  const uniqueId = () => 'song-'+Math.random().toString(36).slice(2,9)+'-'+Date.now();
  const safeHttp = v => { try{const u=new URL(v);return ['http:','https:'].includes(u.protocol) ? u.href : '';}catch{return '';} };
  const ytId = value => {
    const v=safeHttp(value);if(!v) return '';
    try {const u=new URL(v); if(u.hostname==='youtu.be'||u.hostname==='www.youtu.be')return /^[a-zA-Z0-9_-]{11}$/.test(u.pathname.slice(1))?u.pathname.slice(1):'';
      if(/(^|\.)youtube\.com$/.test(u.hostname)||u.hostname==='music.youtube.com') {let id=u.searchParams.get('v')||u.pathname.match(/\/(?:shorts|embed|live)\/([a-zA-Z0-9_-]{11})/)?.[1]||'';return /^[a-zA-Z0-9_-]{11}$/.test(id)?id:'';} return '';
    }catch{return '';}
  };
  /* 반주(MR)는 YouTube 링크(mrUrl) 또는 저장소에 함께 올린 음원 파일(mrAudioUrl) 둘 다 지원한다.
     mrAudioUrl 은 'media/xxx.mp3' 같은 상대 경로(저장소 안 파일)나 https 음원 주소만 허용한다. */
  const mrAudioUrlOf = v => { const t=String(v||'').trim(); if(/^https?:\/\//i.test(t))return t; return /^[\w./-]+\.(mp3|m4a|wav|ogg)$/i.test(t)?t:''; };
  const mrAudioOf = s => mrAudioUrlOf(s&&s.mrAudioUrl);
  const hasMr = s => !!(s && (String(s.mrUrl||'').trim() || mrAudioOf(s)));
  const PLAYLIST_URL = seed.meta.originalPlaylist;
  const PLAYLIST_ID = seed.meta.playlistId;
  const youtubeSearch=s=>`https://www.youtube.com/results?search_query=${encodeURIComponent(s.title+' '+s.artist+' 라이브')}`;
  const musicSearch=s=>`https://music.youtube.com/search?q=${encodeURIComponent(s.title+' '+s.artist)}`;
  const openTab = url => {const u=safeHttp(url);if(u)window.open(u,'_blank','noopener,noreferrer');};
  const selectField = (name,opts,value) => `<select name="${name}" class="input">${opts.map(o=>{const [v,l]=Array.isArray(o)?o:[o,o];return `<option value="${esc(v)}" ${v===value?'selected':''}>${esc(l)}</option>`;}).join('')}</select>`;
  const bar = () => `<header class="topbar"><a class="brand" href="#home" data-nav="home"><span class="brand-icon">♫</span><span><span class="brand-name">STRUM</span><span class="brand-sub">MY PRACTICE STUDIO</span></span></a><nav class="nav" aria-label="주요 메뉴">${navs.map(([id,label])=>`<button data-nav="${id}" class="${id===currentTab?'active':''}" aria-current="${id===currentTab?'page':'false'}">${label}</button>`).join('')}</nav><div class="top-right"><span class="pill">AeroBand Guitar</span></div></header>`;
  const head = (sm,title,sub='',right='')=>`<div class="section-heading"><div><div class="eyebrow">${sm}</div><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div>${right}</div>`;
  const daysView=()=>{const first=weekStart(),today=dateKey(),logs=new Set(weekStats().ls.map(l=>l.date));return ['월','화','수','목','금','토','일'].map((lab,i)=>{const d=new Date(first);d.setDate(d.getDate()+i);const key=dateKey(d);return `<div class="day ${logs.has(key)?'done':''} ${key===today?'today':''}"><span>${lab}</span><span class="day-dot">${logs.has(key)?'✓':d.getDate()}</span></div>`;}).join('')};
  const beatCount = ts => ts==='3/4' ? 3 : ts==='6/8' ? 6 : 4;
  const stageChip = n => n ? `<span class="stage-chip s${n}">STAGE ${n}</span>` : '';
  function chartBadge(s){const c=chartOf(s);
    if(s.category==='reference') return `<span class="tag muted">비음악·참고 영상</span>`;
    if(s.category==='original'&&!c) return `<span class="tag muted">자작곡 · 채보 필요</span>`;
    if(!c) return `<span class="tag muted">${s.category==='pending'?'코드 검수 대기':'코드 검수 대기'}</span>`;
    return `<span class="tag chart-tag">${s.category==='original'?'음원 분석 · ':''}남자키 <b>${esc(c.maleKey||s.maleKey||'—')}</b>${Number.isFinite(c.capo)?` · Capo +${c.capo}`:''} · ${esc(c.timeSignature||'—')}${c.bpm?` · ${c.bpm}BPM`:''}${c.status==='partial'?' · 부분 확인':''}</span>`;}

  function home(){let w=weekStats(), curated=songCount(), ready=buskingCount(),setlist=state.songs.filter(s=>s.setlist).slice(0,5);
    const charted=readySongs().length, pending=pendingSongs().length;
    return `<section class="hero"><div><div class="eyebrow">MAKE A LITTLE PROGRESS, EVERY DAY</div><h1>오늘도, 한 곡에<br>가까워지는 시간.</h1><p>하루 25분의 작은 연습이 낯선 도시의 첫 무대가 됩니다. 남자키로 바꾼 원터치 악보와 4단계 커리큘럼으로 쌓아갑니다.</p>${action('start-practice','오늘의 연습 시작 ↗','btn accent')}</div><div class="hero-badge"><div class="hero-num">${ready}<span> / 3</span></div><p>나의 첫 무대 준비된 곡</p></div></section>
    <div class="playlist-callout"><div><b>🎸 남자키 원터치 악보 ${charted}곡 준비 완료</b><p class="tiny">남성 원곡은 원키 그대로, 여성 원곡만 -5키 · AeroBand Capo 값 · 4/4·3/4·6/8 박자 · BPM까지 넣었습니다. ${pending?`코드 검수 대기 ${pending}곡은 코드표를 확인한 뒤 채웁니다.`:'코드가 확인되지 않아 비워 둔 곡은 없습니다.'}</p></div>${action('go-roadmap','로드맵 열기','btn outline small')}</div>
    ${head('THIS WEEK','이번 주의 리듬','주 5일 연습을 목표로, 적게라도 꾸준히.')}<section class="cards3"><div class="card"><div class="metric-label">이번 주 연습일</div><div class="metric">${w.days} <span>/ ${state.settings.weeklyGoal}일</span></div><div class="progress"><i style="width:${Math.min(100,Math.round(w.days/state.settings.weeklyGoal*100))}%"></i></div></div><div class="card"><div class="metric-label">누적 연습 시간</div><div class="metric">${w.total} <span>분</span></div></div><div class="card"><div class="metric-label">악보 준비된 곡</div><div class="metric">${charted} <span>/ ${curated}곡 정보</span></div><div class="tiny">원본 재생목록 210개 항목 반영</div></div></section>
    <section class="dashboard-grid" style="margin-top:15px"><div class="card"><div class="row between"><h3>이번 주 출석</h3><span class="tiny">오늘 ${new Intl.DateTimeFormat('ko-KR',{dateStyle:'medium'}).format(new Date())}</span></div><div class="weekdays">${daysView()}</div><div class="divider"></div><p class="tiny">오늘 단 20분이어도 기록하면 출석이 쌓입니다.</p></div><div class="card"><div class="eyebrow">YOUR NEXT FOCUS</div><h3 style="margin:5px 0 12px">지금 먼저 연습할 것</h3><div class="stack"><div>01 · <b>원터치 버튼 4개</b> <span class="muted">— Capo +2, C폼으로 5분</span></div><div>02 · <b>2·4박 척킹</b> <span class="muted">— 60 BPM에서 손날 뮤트 5분</span></div><div>03 · <b>후렴 연결</b> <span class="muted">— 멈추지 않고 4마디 10분</span></div></div></div></section>
    ${head('YOUR FIRST SETLIST','나의 첫 세트리스트','실제로 연주할 곡 3개부터 준비하세요.',action('go-songs','전체 곡 보기','btn outline small'))}
    <div class="card">${setlist.length?setlist.map((s,i)=>`<div class="setrow"><div><b>${i+1}. ${esc(s.title)}</b> <span class="tiny">${esc(s.artist)}</span></div>${stat(s.level)}</div>`).join(''):`<div class="empty"><strong>아직 선택한 세트리스트가 없습니다.</strong>곡 목록에서 무대에 올릴 노래를 선택하세요.</div>`}<div class="row between" style="margin-top:13px"><span class="tiny">전체 버스킹 가능 ${ready}곡 · 목표 최소 3곡</span>${action('go-songs','곡 선택하기','btn primary small')}</div></div>
    <p class="alert" style="margin-top:16px"><b>데이터 반영 안내</b> · ${state.songs.length}개 항목 기준 <b>악보 완료 ${categoryCount('chart')}</b> · 부분 확인 ${categoryCount('partial')} · 코드 검수 대기 ${categoryCount('pending')} · 비음악·참고 ${categoryCount('reference')} · 자작곡 ${categoryCount('original')}. 확인 전 값을 임의로 채우지 않습니다. <button class="btn small outline" data-nav="settings">JSON/CSV 가져오기</button></p>`;
  }
  const displayTitle = s => s.workTitle || s.title;
  const displayArtist = s => s.workArtist || s.artist;
  function songRow(s,i){const c=chartOf(s);
    return `<article class="song-row"><div class="song-num">${String(i+1).padStart(2,'0')}</div><div><div class="song-name">${esc(displayTitle(s))} ${c?stageChip(c.stage):''}</div><div class="song-artist">${esc(displayArtist(s))}${s.sourceIndices?.length?` · 원본 #${s.sourceIndices.join(', #')}`:''}</div><div class="taglist">${chartBadge(s)}${s.videoStatus&&s.videoStatus!=='공개 영상'?`<span class="tag">${esc(s.videoStatus)}</span>`:''}${s.tags?.slice(0,2).map(t=>`<span class="tag">${esc(t)}</span>`).join('')||''}${s.verification.startsWith('learning-')?'<span class="tag">외부 추천곡</span>':''}</div></div>${stat(s.level)}<div class="song-actions">${c?action('chart:'+s.id,'악보','btn primary small'):action('chart:'+s.id,'정보','btn outline small')}${action('video:'+s.id,'영상')}${action('music:'+s.id,'음악')}${action('mr:'+s.id,hasMr(s)?'MR':'MR 없음','btn small '+(hasMr(s)?'mr-on':'mr-off'))}${action('edit:'+s.id,'수정','btn outline small')}</div></article>`}
  const songQuery = () => {const raw=String(searchQuery).trim().replace(/\s*번$/,'');const hash=raw.startsWith('#');const body=hash?raw.slice(1).trim():raw;return {q:norm(body),n:/^\d{1,3}$/.test(body)?+body:null,hash};};
  function filterSongs(){const {q,n,hash}=songQuery();return ordered().filter(s=>{const fields=[s.title,s.artist,s.workTitle,s.workArtist,s.notes,s.chords,...(s.tags||[]),...(s.sourceIndices||[]),s.maleKey,s.key];let hit;if(n!==null){hit=(s.sourceIndices||[]).includes(n)||(!hash&&[s.title,s.artist].some(v=>new RegExp('(^|[^0-9])'+n+'([^0-9]|$)').test(norm(v))));}else{hit=!q||fields.some(v=>norm(v).includes(q));}
      const st=statusFilter;const cat=s.category||'';
      const stateHit=st==='all'?true:st==='setlist'?s.setlist
        :st==='chart-ready'?cat==='chart'
        :st==='chart-partial'?cat==='partial'
        :st==='chart-pending'?(cat==='pending'||s.chartStatus==='pending')
        :st==='original'?(cat==='original'||!!s.needsChart)
        :st==='reference'?cat==='reference'
        :s.level===st;
      return hit&&stateHit;});}
  function songsPage(){const filtered=filterSongs();
    const m=seed.meta||{}, cat=n=>state.songs.filter(x=>(x.category||'')===n).length;
    const chips=[['chart-ready','악보 완료',cat('chart')],['chart-partial','부분 확인',cat('partial')],['chart-pending','검수 대기',cat('pending')],['original','자작·AI곡',cat('original')],['reference','비음악·참고',cat('reference')]];
    return `${head('MY SONG LIBRARY','나의 버스킹곡','곡 검색 · 남자키/카포 · 원터치 악보 · 숙련도를 한곳에서',action('new-song','+ 새 곡 등록','btn primary'))}
    <div class="alert" style="margin-bottom:12px"><b>전체 ${state.songs.length}개 항목 정리</b> — 남자키·박자·BPM·원터치 악보 <b>${cat('chart')}개</b>(서로 다른 곡 ${m.uniqueChartSongCount||'—'}곡) · 부분 확인 ${cat('partial')} · 코드 검수 대기 ${cat('pending')} · 비음악·참고 ${cat('reference')} · 자작곡 ${cat('original')}. 여자키 원곡만 <b>-5키</b>, 남성 원곡은 <b>원키 그대로</b>를 남자키로 잡고 AeroBand Capo를 맞췄습니다. 마디 배치는 공개된 코드표를 4박 카드로 정리한 연습용입니다.</div>
    <div class="row" style="flex-wrap:wrap;gap:6px;margin-bottom:12px">${chips.map(([v,l,n])=>`<button class="btn small ${statusFilter===v?'primary':'outline'}" data-act="filter-cat:${v}">${l} ${n}</button>`).join('')}</div>
    <div class="toolbar" style="margin-bottom:13px"><div class="search-wrap"><span class="search-mark">⌕</span><input id="song-search" class="input" aria-label="곡 검색" placeholder="곡명, 가수, 남자키, 원본 번호 검색" value="${esc(searchQuery)}" /></div><select id="song-filter" class="select"><option value="all">모든 항목</option><option value="chart-ready" ${statusFilter==='chart-ready'?'selected':''}>악보 완료</option><option value="chart-partial" ${statusFilter==='chart-partial'?'selected':''}>부분 확인</option><option value="chart-pending" ${statusFilter==='chart-pending'?'selected':''}>검수 대기</option><option value="original" ${statusFilter==='original'?'selected':''}>자작·AI곡(채보 필요)</option><option value="reference" ${statusFilter==='reference'?'selected':''}>비음악·참고 영상</option><option value="setlist" ${statusFilter==='setlist'?'selected':''}>내 세트리스트</option>${levels.map(l=>`<option value="${l}" ${statusFilter===l?'selected':''}>${l}</option>`).join('')}</select></div>
    <div class="tiny" id="song-result-count" style="margin-bottom:8px">검색 결과 ${filtered.length}개 · 데이터가 추가되면 즉시 반영됩니다.</div>
    <section class="song-list" id="song-list">${filtered.length?filtered.map(songRow).join(''):'<div class="empty">검색된 항목이 없습니다.</div>'}</section>
    <div class="card" style="margin-top:16px"><div class="row between"><h3>채보가 필요한 자작·AI곡</h3><span class="tiny">음원을 주시면 채보 대상</span></div><p class="tiny">인터넷에 악보가 확인되지 않아 코드를 지어내지 않은 항목입니다. 주성 님이 음원이나 fal 채보를 붙이면 여기에 악보를 추가합니다.</p><div class="stack" style="margin-top:10px">${state.songs.filter(s=>(s.category==='original'&&!chartOf(s))||(s.category==='pending'&&s.needsChart)).map(s=>`<div class="tiny">· <b>${esc(displayTitle(s))}</b> ${esc(displayArtist(s))} — ${esc(s.categoryNote||s.chartNote||'코드 확인 필요')}</div>`).join('')||'<div class="tiny">해당 항목이 없습니다.</div>'}</div></div>`;
  }
  function playlistPage(){
    const direct=safeHttp(PLAYLIST_URL);
    const embed='https://www.youtube-nocookie.com/embed/videoseries?list='+encodeURIComponent(PLAYLIST_ID);
    return `${head('ORIGINAL YOUTUBE PLAYLIST','내 버스킹 원본 재생목록','원본 재생목록 210개 항목을 확인했습니다. 공개 168개 영상은 곡 라이브러리와 원본 슬롯에 연결했고, 접근 불가 42개는 사유만 기록했습니다.')}
    <div class="alert" style="margin-bottom:14px"><b>중요:</b> 이 화면은 원본 재생목록을 YouTube 공식 플레이어로 재생합니다. 곡과 연결한 것은 공개 168개 영상뿐이며, 해지·삭제·비공개 42개에는 가짜 URL을 넣지 않았습니다.</div>
    <div class="card"><div class="player playlist-player"><iframe loading="lazy" title="내 버스킹 유튜브 재생목록" src="${embed}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>
    <div class="row" style="flex-wrap:wrap;margin-top:15px"><a class="btn primary" href="${esc(direct)}" target="_blank" rel="noopener noreferrer">YouTube에서 재생목록 열기 ↗</a>${action('go-songs','곡별 학습 목록','btn outline')}${action('go-sources','원본 번호 확인','btn outline')}</div>
    <p class="tiny" style="margin-top:11px">저작권 보호 및 YouTube 재생 정책을 준수합니다. 영상 재생을 숨기고 오디오만 추출하지 않습니다. 모바일에서 임베드가 제한되면 YouTube 직접 열기를 이용하세요.</p></div>`;
  }

  /* ── 성장 로드맵 ─────────────────────────────────────────── */
  function stageSongs(n){return ordered().filter(s=>{const c=chartOf(s);if(!c) return false;return n===4 ? !!c.percussiveReady : Number(c.stage)===n;});}
  function roadmapPage(){
    const teach=[
      ['버튼 위치를 눈으로 익히기 — 4/4 한 박에 한 번 다운, 60→70 BPM','코드 4개짜리 곡으로 8마디 완주','낯선 코드는 왼손이 문제라고 느끼게 되는 단계'],
      ['카포만 바꿔 같은 진행을 3개 키로 옮기기','3/4·6/8로 바꿔보기 (6/8은 1·4박 강세)','카포 숫자만 바꿔 노래방 키가 되는 경험'],
      ['오픈 코드와 약식 바레 전환','한 마디에 코드 2개(2박씩) 바꾸기','SimplifyChord 슬롯으로 어려운 코드를 버튼처럼 쓰기'],
      ['컷과 뮤트','4박 뒤 컷 → 2·4박 척킹 → 바디 타격','손목으로 박을 만드는 감각']
    ];
    return `${head('GROWTH ROADMAP','성장 로드맵','오른손 → 코드 전환 → 정식 코드 → 퍼커시브. 지루하지 않게 4단계로 나눴습니다.')}
    <div class="alert" style="margin-bottom:16px">각 곡은 <b>남자키 · AeroBand Capo 값 · 박자 · BPM · 원터치 악보</b>가 함께 표시됩니다. 같은 곡을 단계만 바꿔 다시 쓰기 때문에 외울 곡을 늘리지 않아도 됩니다.</div>
    ${STAGES.map(st=>{const list=stageSongs(st.n);return `<section class="card stage-card" style="--stage:${st.color}"><div class="row between stage-head"><div><div class="eyebrow">STAGE ${st.n}</div><h3>${esc(st.title)}</h3><p class="tiny">${esc(st.sub)}</p></div><span class="stage-count">${list.length}곡</span></div>
      <div class="stage-teach">${teach[st.n-1].map((t,i)=>`<div><b>0${i+1}</b> ${esc(t)}</div>`).join('')}</div>
      <div class="stage-songs">${list.length?list.map(s=>{const c=chartOf(s);return `<button class="song-chip" data-act="chart:${esc(s.id)}"><b>${esc(s.title)}</b><span>${esc(s.artist)}</span><em>${esc(c.maleKey)}키 · Capo +${c.capo} · ${esc(c.timeSignature)} · ${c.bpm}BPM</em></button>`;}).join(''):'<p class="tiny">이 단계 곡은 아직 없습니다.</p>'}</div></section>`;}).join('')}
    ${head('NO-BORING CURRICULUM','안 질리는 연습 순서','매 세션: 복습 1곡 + 새 곡 1곡 + 재미 1곡. 템포·분위기를 섞어 25분을 채웁니다.')}
    <div class="card"><div class="curriculum">${curriculum().map((row,i)=>`<div class="cur-row"><span class="cur-num">${i+1}</span><div class="grow"><b>${esc(row.title)}</b><div class="tiny">${esc(row.reason)}</div></div><span class="tag">${esc(row.kind)}</span>${action('chart:'+row.id,'악보','btn small')}</div>`).join('')}</div>
    <div class="hint" style="margin-top:12px"><b>퍼커시브 단계 순서</b> · ① 4박 뒤 컷(손바닥으로 줄 막기) ② 2·4박 척킹(X) ③ 2·4박 바디 톡(브릿지 옆) ④ 컷+톡 조합 ⑤ 곡 후렴에만 적용 → 완곡. 각 동작은 60 BPM에서 4마디씩 반복하고, 10분 넘게 같은 동작을 붙잡지 않습니다.</div>
    </div>`;
  }
  function curriculum(){
    const order=[
      ['restored-146','Way Back Home','Em–C–D–G 네 코드, 2박마다 교대 — 오른손 8비트 시작','Stage 1'],
      ['verified-003','Thank You','코드 1개가 1마디, 가장 정직한 4/4','Stage 1'],
      ['verified-013','Flower','I–vi–IV–V, 후렴이 바로 나온다','Stage 1'],
      ['restored-144','기억을 걷는 시간','오픈 코드 4개, 16비트 감각','Stage 1'],
      ['verified-007','한숨','슬로우 고고 62BPM, 2박마다 코드','Stage 1'],
      ['restored-132','사랑하게 될 거야','B7 하나만 슬롯, 백비트 곡','Stage 2'],
      ['restored-123','안아줘','F↔Fm 전환, 약식 바레 연습','Stage 2'],
      ['verified-010','도망가자','Capo +3 C폼, Am 하나만 슬롯','Stage 2'],
      ['verified-016','How To Cry','영어 발음 + 느린 8분','Stage 2'],
      ['verified-012','TOMBOY','Cm 슬롯 1개, 브릿지 컷','Stage 2'],
      ['restored-142','청혼하지 않을 이유를 못 찾았어','Bm7 슬롯, 96BPM','Stage 2'],
      ['restored-125','미안해 미워해 사랑해','E키 발라드, Am 컬러 코드','Stage 2'],
      ['verified-020','오르막길','반음 전조 체험(카포 이동)','Stage 3'],
      ['verified-006','희재','C#m7·F#7 슬롯 3개, 느린 발라드','Stage 3'],
      ['verified-001','오늘','F#·G#·C#m, 손이 바빠지는 곡','Stage 3'],
      ['restored-130','첫눈처럼 너에게 가겠다','단조 4키 내림, 후렴 다이내믹','Stage 3'],
      ['verified-025','히로인','일본어 + 전위 코드','Stage 3'],
      ['verified-022','세상이 그대를 속일지라도','감정 기복 큰 고음 발라드','Stage 3'],
      ['restored-096','And July','2·4박 척킹이 곡의 전부','Stage 4'],
      ['restored-151','Lonely','가볍게 치는 현악 느낌','Stage 4'],
      ['verified-018','たぶん','빈 박에 척킹 넣기','Stage 4'],
      ['verified-002','민들레','칼립소+바디 톡','Stage 4'],
      ['restored-102','눈이 오잖아','겨울 버스킹, 후렴 컷','Stage 4'],
      ['verified-015','Englishman in New York','스카 척, 손날 뮤트의 정석','Stage 4']
    ];
    return order.filter(([id])=>song(id)).map(([id,t,r,k])=>({id,title:t,reason:r,kind:k}));
  }

  /* ── 오늘의 연습 ─────────────────────────────────────────── */
  function stageTasks(){const mode=state.settings.mode,base=mode==='easy'?'원터치 코드 전환':'정식 코드 운지 연습';const focus=song(state.settings.focusSongId);const c=focus?chartOf(focus):null;return [
    ['손 풀기 & 준비',c?`${focus.title} · Capo +${c.capo} 설정 확인 · ${c.timeSignature} 메트로놈`:'어깨 힘 빼기 · 에어로밴드 연결 및 볼륨 확인',3],
    [base,mode==='easy'?'원터치 버튼 위치 확인, Em↔Am 전환':'정식 Em·Am·C·D의 손가락 위치 연습',5],
    ['리듬 & 스트로크',c?`${c.stroke||'8분 다운 스트로크'}`:'60 BPM부터 · 한 박에 한 번 다운',5],
    ['후렴 네 마디 연결','멈추지 않고 네 마디 연결 · 필요하면 템포 낮추기',Math.max(5,state.settings.minutes-15)],
    ['오늘의 기록','실수, 코드, 다음 목표 한 줄 기록하기',2]
  ];}
  function practicePage(){const tasks=stageTasks(),done=state.completedStages.length;const focus=song(state.settings.focusSongId);const c=focus?chartOf(focus):null;
    return `${head('TODAY’S SESSION','오늘의 '+state.settings.minutes+'분 루틴','원터치 코드부터 퍼커시브까지, 오늘 쓸 곡 하나만 정해서')}
    <section class="two-col"><div class="card"><div class="row between"><h3>나의 연습 루틴</h3><span class="pill">${done}/5 완료</span></div>
      ${c?`<div class="focus-strip"><div><b>오늘의 곡 · ${esc(focus.title)}</b><div class="tiny">${esc(c.maleKey)}키 · Capo +${c.capo} · ${esc(c.timeSignature)} · ${c.bpm}BPM</div></div>${action('chart:'+focus.id,'악보 보기','btn small')}</div>`:''}
      <div class="row between" style="margin-top:14px"><div class="segmented">${[20,25,30].map(v=>`<button data-act="minutes:${v}" class="${state.settings.minutes===v?'selected':''}">${v}분</button>`).join('')}</div><div class="segmented"><button data-act="mode:easy" class="${state.settings.mode==='easy'?'selected':''}">원터치</button><button data-act="mode:standard" class="${state.settings.mode==='standard'?'selected':''}">정식 코드</button></div></div>
      <div class="routine-steps">${tasks.map(([title,description,time],i)=>`<label class="task"><input type="checkbox" data-step="${i}" ${state.completedStages.includes(i)?'checked':''}/><div class="grow"><b>${esc(title)}</b><div class="small-desc">${esc(description)}</div></div><span class="minute">${time}분</span></label>`).join('')}</div>
      <div class="hint">원터치 코드(Easy Chord)와 SimplifyChord(손가락 수를 줄인 코드)는 서로 다른 기능입니다. 원터치는 화면 버튼 10개, SimplifyChord는 프렛마다 코드 하나를 등록합니다(공식 안내 기준 최대 12개, 화면에는 8칸까지 표시).</div></div>
      <div class="stack"><div class="card meter"><div class="eyebrow">FOCUS TIMER</div><h3>나의 집중 타이머</h3><div class="timer" id="timer-display">${mins(remaining)}</div><div class="row" style="justify-content:center;flex-wrap:wrap">${action('timer-toggle',sessionRunning?'일시정지':'연습 시작','btn primary')}${action('timer-reset','초기화','btn outline')}</div>
      <div class="divider"></div>
      <div class="row between"><div><h3>나의 메트로놈</h3><p class="tiny">${esc(state.settings.timeSignature)} · ${state.settings.timeSignature==='6/8'?'8분음표 6번, 1·4박 강세':'1박 강세'}</p></div><span id="bpm-label" style="font-size:23px;font-weight:900">${state.settings.bpm} BPM</span></div>
      <div class="segmented ts-pick" style="margin-top:10px">${['4/4','3/4','6/8'].map(t=>`<button data-act="ts:${t}" class="${state.settings.timeSignature===t?'selected':''}">${t}</button>`).join('')}</div>
      <p class="tiny" style="margin:6px 0 0">악보에 표시된 박자를 기준으로 연습하세요. 확인된 곡은 대부분 4/4이고, 박자표를 확인하지 못한 곡은 4/4로 단정하지 않았습니다. 3/4·6/8은 왈츠·겹박자 기본 스트로크를 따로 연습할 때 쓰세요.</p>
      <div class="beat-dots" id="beat-dots">${Array.from({length:beatCount(state.settings.timeSignature)},(_,i)=>`<i class="${i===0?'accent':''}"></i>`).join('')}</div>
      <input id="bpm-range" type="range" min="40" max="180" step="1" value="${state.settings.bpm}" aria-label="BPM" style="width:100%;margin:12px 0" /><div class="row between">${action('bpm-down','−5','btn outline small')}${action('metro-toggle',metronome?'메트로놈 정지':'메트로놈 켜기','btn primary small')}${action('bpm-up','+5','btn outline small')}</div></div>
      <div class="card"><h3>원터치 버튼 10개</h3><p class="tiny" style="margin:4px 0 12px">에어로밴드 앱과 같은 색으로 표시합니다.</p><div class="ot-grid">${BTNS.map(b=>`<div class="ot-btn" style="--c:${BTN_COLOR[b]}">${b}</div>`).join('')}</div></div></div></section>
    ${head('PRACTICE LOG','오늘의 연습 기록','연습 종료 후 저장하면 이번 주 출석에 반영됩니다.')}
    <div class="card"><form id="practice-form" class="stack"><div class="field-grid"><div class="field"><label>연습한 곡</label><select name="songId" class="input"><option value="">기초 코드 연습 (곡 선택 없음)</option>${ordered().map(s=>`<option value="${esc(s.id)}" ${s.id===state.settings.focusSongId?'selected':''}>${esc(s.title)} — ${esc(s.artist)}</option>`).join('')}</select></div><div class="field"><label>실제 연습 시간 (분)</label><input type="number" name="minutes" value="${state.settings.minutes}" min="1" max="480" required /></div><div class="field"><label>연습 코드</label><input name="chords" placeholder="예: Em, Am, G, D" value="${c?esc(c.sections[1]?.bars.flat().map(x=>x.sound).join(', ')||''):''}" /></div><div class="field"><label>오늘 스트로크/리듬</label><input name="strum" placeholder="예: 다운 스트로크 60 BPM" value="${c?esc(c.stroke||''):''}" /></div></div><div class="field"><label>잘 안된 부분 · 다음에 할 일</label><textarea name="memo" placeholder="Em→Am 전환할 때 2박 늦음. 내일 55BPM에서 다시 연습"></textarea></div><button class="btn primary" type="submit">오늘 연습 저장하기</button></form></div>`;
  }
  function logsPage(){let logs=[...state.logs].sort((a,b)=>(b.date||'').localeCompare(a.date||'')||(b.id||'').localeCompare(a.id||''));let total=state.logs.reduce((s,l)=>s+Number(l.minutes||0),0);
    return `${head('YOUR PROGRESS','나의 연습 기록','연습일 · 누적 시간 · 실수와 다음 목표를 돌아봅니다.')}<div class="cards3"><div class="card"><div class="metric-label">전체 연습 횟수</div><div class="metric">${state.logs.length}<span>회</span></div></div><div class="card"><div class="metric-label">전체 누적 시간</div><div class="metric">${total}<span>분</span></div></div><div class="card"><div class="metric-label">연습한 날짜</div><div class="metric">${new Set(state.logs.map(l=>l.date)).size}<span>일</span></div></div></div>
    ${head('PRACTICE HISTORY','날짜별 기록','','')}
    ${logs.length?`<div class="stack">${logs.map(l=>`<article class="card"><div class="row between"><div><b>${esc(l.date)}</b> <span class="tag">${esc(l.minutes)}분</span><p class="tiny">${esc(song(l.songId)?.title||'기초 코드 연습')} · ${l.mode==='standard'?'정식 코드':'원터치 코드'}</p></div>${action('delete-log:'+l.id,'삭제','btn danger small')}</div><div class="divider"></div><div class="tiny">연습 코드: ${esc(l.chords||'—')} · 스트로크: ${esc(l.strum||'—')}</div>${l.memo?`<p class="pre" style="margin-top:8px">${esc(l.memo)}</p>`:''}</article>`).join('')}</div>`:'<div class="empty"><strong>아직 기록이 없습니다.</strong>오늘 기타를 잡은 시간이 첫 번째 기록이 됩니다.</div>'}`;
  }
  function sourcesPage(){const known=state.sources.filter(s=>s.songs?.length).length, unavailable=state.sources.filter(s=>s.status==='접근 불가').length, publicCount=state.sources.filter(s=>s.status==='확인').length;
    let q=norm(sourceQuery);let filtered=state.sources.filter(s=>{
       let ok=(!q||String(s.index).includes(q)||norm(s.url).includes(q)||norm(s.note).includes(q)||s.songs.some(id=>norm(song(id)?.title).includes(q)));
       return ok&&(sourceFilter==='all'||(sourceFilter==='known'?s.songs.length>0:s.status===sourceFilter));
    }); const display=showAllSources?filtered:filtered.slice(0,50);
    return `${head('SOURCE LIBRARY','원본 211개 영상 관리','영상 번호는 유지하고, 묶음 영상의 여러 노래는 따로 관리합니다.')}
    <div class="alert" style="margin-bottom:15px">211개는 <b>원본 영상 번호 슬롯</b>입니다. 2026-11-22 재생목록 재확인으로 공개 <b>${publicCount}개</b> 영상의 제목·URL, 접근 불가 <b>${unavailable}개</b>의 사유(계정 해지·비공개·저작권 삭제·업로더 삭제)를 기록했습니다. 곡이 연결된 슬롯 ${known}개, #163은 제외 유지, #211은 영상 미확인입니다.</div>
    <div class="toolbar" style="margin-bottom:12px"><div class="search-wrap"><span class="search-mark">⌕</span><input id="source-search" class="input" placeholder="원본 번호 / 곡명 검색" value="${esc(sourceQuery)}" /></div><select id="source-filter" class="select"><option value="known" ${sourceFilter==='known'?'selected':''}>곡이 확인된 번호</option><option value="all" ${sourceFilter==='all'?'selected':''}>211개 전체</option>${SOURCE_STATES.map(l=>`<option value="${l}" ${sourceFilter===l?'selected':''}>${l}</option>`).join('')}</select></div>
    <div class="card" style="padding:0 10px"><div class="table-scroll"><table class="source-table"><thead><tr><th>번호</th><th>연결된 곡</th><th>상태</th><th>원본 영상 · 제목</th><th>편집</th></tr></thead><tbody>${display.map(s=>`<tr><td>#${s.index}</td><td class="title-cell">${s.songs.length?s.songs.map(id=>{const x=song(id);if(!x)return '';return x.verification==='playlist-public-video'?`<span class="muted">[영상] ${esc(x.title)}</span>`:esc(x.title);}).join(', '):'<span class="muted">미확인</span>'}</td><td>${stat(s.status)}</td><td class="video-cell">${s.title?`<div class="tiny">${esc(s.title.length>70?s.title.slice(0,70)+'…':s.title)}</div>`:''}${s.url?`<a href="${esc(safeHttp(s.url))}" target="_blank" rel="noopener noreferrer">영상 열기</a>`:(s.reason?`<span class="muted">${esc(s.reason)}</span>`:'<span class="muted">미등록</span>')}</td><td>${action('source:'+s.index,'수정','btn small')}</td></tr>`).join('')}</tbody></table></div></div>
    <div class="row between" style="margin-top:13px"><span class="tiny">${display.length}/${filtered.length}개 표시 중</span>${display.length<filtered.length?action('more-sources','모든 번호 보기','btn outline small'):''}</div>`;
  }
  function settingsPage(){return `${head('DATA & SETTINGS','백업·복원·설정','다른 휴대폰 또는 새 서버로 옮길 때 전체 데이터를 보존하세요.')}
     <div class="two-col"><section class="card stack"><h3>내 데이터 백업</h3><p class="tiny">전체 백업(JSON)은 곡, 211개 원본 번호, 숙련도, 세트리스트, 연습 기록을 모두 포함합니다. 인터넷 서버에 자동 동기화되지는 않습니다.</p><div class="backup-list">${action('export-json','전체 JSON 백업','btn primary')}${action('export-csv','곡 목록 CSV','btn outline')}${action('export-charts','악보 설정 CSV','btn outline')}${action('export-sources','211 원본 CSV','btn outline')}</div><div class="divider"></div><h3>데이터 가져오기</h3><p class="tiny">전체 백업 JSON 또는 CSV(곡명·가수 필수)를 가져옵니다. 기존 자료를 삭제하지 않고 병합하거나 백업 파일로 교체할 수 있습니다.</p><div class="field"><label>JSON 또는 CSV 파일 선택</label><input type="file" id="import-file" accept=".json,.csv,application/json,text/csv" class="input" /></div><div class="field"><label>가져오기 방법</label><select id="import-mode" class="input"><option value="merge">기존 데이터와 병합(추천)</option><option value="replace">가져온 전체 JSON으로 교체</option></select></div>${action('import-file','가져오기 실행','btn primary')}<div class="hint">구버전 Sites의 브라우저 내부 데이터는 출처가 다른 이 사이트로 자동 이전되지 않습니다. 원본 파일이 있다면 이 화면에서 가져오세요.</div></section>
      <section class="card stack"><h3>사용 환경</h3><div class="field"><label>일주일 연습 목표</label><select id="weekly-goal" class="input">${[3,4,5,6,7].map(n=>`<option ${state.settings.weeklyGoal===n?'selected':''} value="${n}">${n}일</option>`).join('')}</select></div><div class="field"><label>기본 연습 경로</label>${selectField('mode',MODE_OPTIONS,state.settings.mode)}</div><div class="field"><label>기본 박자</label>${selectField('ts',[['4/4','4/4'],['3/4','3/4'],['6/8','6/8']],state.settings.timeSignature)}</div><div class="divider"></div><h3>악보 데이터</h3><p class="tiny">남자키·박자·BPM·원터치 악보 ${readySongs().length}곡 · 부분 확인 ${state.songs.filter(s=>s.chartStatus==='partial').length}곡 · 검수 대기 ${pendingSongs().length}곡</p><p class="tiny">${esc(seed.meta.chartDisclosure||'')}</p><div class="divider"></div><h3>기존 프로젝트 정보</h3><p>기존 게시 사이트: <a class="footer-link" target="_blank" rel="noopener noreferrer" href="${esc(seed.meta.originalSite)}">STRUM 원본 열기</a></p><p class="tiny">원본 211영상 슬롯 · 재생목록 210개 항목 확인(공개 168·접근 불가 42) · 곡 라이브러리 ${songCount()}개</p><p class="notice tiny">※ 이 파일은 원본 프로젝트의 정확한 소스코드 덤프가 아닌 기능 재구현입니다.</p><div class="divider"></div><h3>기존 연습 데이터 안전하게 관리</h3><p class="tiny">브라우저 저장소가 초기화되면 데이터가 사라질 수 있습니다. 주기적으로 전체 JSON 백업을 받으세요.</p>${action('clear-data','복원본 데이터 초기화','btn danger')}</section></div>`;}

  /* ── 곡 상세: 원터치 컬러 악보 / SimplifyChord / 퍼커시브 / 근거 ── */
  function chordCell(cell,beats){
    const isSlot=!cell.btn;
    const color=isSlot?'#8b8b7a':BTN_COLOR[cell.btn]||'#8b8b7a';
    const label=isSlot?`S${cell.slot}`:cell.btn;
    const sub=isSlot?`${esc(cell.sound)}`:`${esc(cell.btn)}`;
    return `<div class="cc ${isSlot?'is-slot':''}" style="--c:${color};--beats:${beats/cell.__span||beats}"><div class="cc-btn">${esc(label)}</div><div class="cc-sound">${esc(cell.sound)}</div>${cell.orig&&norm(cell.orig)!==norm(cell.sound)?`<div class="cc-orig">원곡 ${esc(cell.orig)}</div>`:''}</div>`;
  }
  function extraNote(c){
    const ext=c.sections.some(sec=>sec.bars.some(b=>b.some(x=>/[0-9]|maj|sus|add|dim|aug/i.test(x.orig||''))));
    return ext?`<p class="tiny" style="margin-top:6px">7th·sus·add·dim 코드는 원터치 버튼의 3화음으로 근사합니다. 각 마디 카드 아래 ‘원곡 …’으로 원래 코드를 함께 적었습니다.</p>`:'';
  }
  function chartSections(c,ts){
    const beats=beatCount(ts);
    return c.sections.map(sec=>`<div class="chart-sec"><div class="row between sec-head"><h4>${esc(sec.name)}</h4><span class="tiny">${sec.bars.length}마디</span></div>
      <div class="bar-row">${sec.bars.map((bar,bi)=>`<div class="bar" aria-label="${bi+1}마디"><div class="bar-beats">${Array.from({length:beats},(_,i)=>`<i class="${i===0?'on':''}"></i>`).join('')}</div><div class="bar-cells">${bar.map(cell=>chordCell(cell,beats)).join('')}</div><div class="bar-num">${bi+1}</div></div>`).join('')}</div></div>`).join('');
  }
  function chartModal(s){
    const c=(s.chart&&s.chart.status!=='pending')?s.chart:null;const tab=modal.tab||'chart';
    const head0=`<div class="chart-head"><div class="keyflow">
        <div><span>원곡 키</span><b>${esc((c&&c.originalKey)||s.key||'—')}</b></div>
        <div><span>남자키</span><b class="hl">${esc((c&&c.maleKey)||s.maleKey||'—')}</b></div>
        <div><span>AeroBand Capo</span><b class="hl">${c&&Number.isFinite(c.capo)?'+'+c.capo:'—'}</b></div>
        <div><span>박자</span><b>${esc((c&&c.timeSignature)||s.timeSignature||'—')}</b></div>
        <div><span>BPM</span><b>${(c&&c.bpm)||s.bpm||'—'}</b></div>
      </div>
      <div class="row" style="flex-wrap:wrap">${hasMr(s)?action('mr:'+s.id,'MR 듣기','btn accent small'):action('mr:'+s.id,'MR 없음','btn outline small')}${c?action('metro-song:'+s.id,'이 곡 템포로 연습','btn primary small'):''}${action('edit:'+s.id,'곡 정보 수정','btn outline small')}</div></div>`;
    const partialStrip=((s.chartStatus==='partial'||s.chartStatus==='original')&&c&&s.chartNote)?`<div class="alert strip"><b>${s.chartStatus==='original'?'음원 분석':'부분 확인'}</b> · ${esc(s.chartNote)}</div>`:'';
    const tabs=`<div class="subtabs">${[['chart','원터치 악보'],['slots','SimplifyChord'],['perc','스트로크·퍼커시브'],['basis','근거']].map(([k,l])=>`<button data-act="chart-tab:${k}" class="${tab===k?'active':''}">${l}</button>`).join('')}</div>`;
    if(!c){
      const pc=s.chart||{};const pev=pc.evidence||[];
      const known=pev.length?`<div class="card" style="margin-top:12px"><h3>확인한 값</h3><div class="kv"><div><span>원곡 키</span><b>${esc(pc.originalKey||'미확인')}</b></div><div><span>박자</span><b>${esc(pc.timeSignature||'미확인')}</b><small>${esc(pc.timeNote||'')}</small></div><div><span>BPM</span><b>${pc.bpm||'—'}</b><small>${esc(pc.bpmNote||'')}</small></div></div><div class="divider"></div><h4>근거 자료</h4><ul class="ev">${pev.map(e=>`<li><a href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${esc(e.label)}</a><span class="tiny">${esc(e.note)}</span></li>`).join('')}</ul><p class="tiny">키·코드가 확인되지 않은 값은 비워 두었습니다. 위 링크에서 악보·코드표를 바로 열 수 있습니다.</p></div>`:'';
      return `${head0}${s.chartStatus==='partial'&&s.chart?`<div class="alert">${esc(s.chartNote||'일부 정보만 확인되었습니다.')}<br>확인된 값: 원키 ${esc(s.chart.originalKey||'—')} · ${esc(s.chart.timeSignature||'—')}${s.chart.bpm?` · ${s.chart.bpm}BPM`:''}</div>`:`<div class="empty"><strong>코드 검수 대기 곡입니다.</strong>${esc(s.chartNote||'원곡 키·박자·코드를 확인한 뒤 악보를 채웁니다. 추측값을 넣지 않습니다.')}</div>`}${known}
      <div class="row" style="margin-top:12px;flex-wrap:wrap">${action('video:'+s.id,'영상 보기','btn outline')}${action('music:'+s.id,'음악 듣기','btn outline')}${hasMr(s)?action('mr:'+s.id,'MR 듣기','btn accent'):action('mr:'+s.id,'MR 없음','btn outline')}</div>`;
    }
    if(tab==='chart'){
      const used=BTNS.filter(b=>c.sections.some(sec=>sec.bars.some(b_=>b_.some(x=>x.btn===b))));
      return `${head0}${tabs}${partialStrip}
        <div class="capo-callout"><b>에어로밴드 앱 하단 <span class="hl">Capo ${c.capo}</span>로 맞추고, 원터치 코드를 켜세요.</b><span>${esc(c.maleKey)}키 · ${esc(c.formText)} · ${used.length}개 버튼 사용 · CAPO+/CAPO− 버튼으로도 조옮김</span></div>
        <div class="legend">${BTNS.map(b=>`<span class="lg ${used.includes(b)?'on':''}" style="--c:${BTN_COLOR[b]}"><i></i>${b}</span>`).join('')}</div>
        ${chartSections(c,c.timeSignature)}
        <div class="stroke-strip"><b>오른손</b> ${esc(c.stroke||'↓ ↓↑ ↑↓↑')}</div>
        ${extraNote(c)}
        <p class="tiny">${esc(c.basis||'')}</p>`;
    }
    if(tab==='slots'){
      const slots=c.slots||[];
      const slotUse=[];
      c.sections.forEach(sec=>sec.bars.forEach((bar,bi)=>bar.forEach(x=>{if(x.slot)slotUse.push({sec:sec.name,bar:bi+1,slot:x.slot,chord:x.sound});})));
      return `${head0}${tabs}
        <div class="capo-callout"><b>에어로밴드 앱 → 원손 단순화 → <span class="hl">SimplifyChord 켜기</span></b><span>${slots.length?`${slots.length}개 슬롯에 아래 코드를 등록하세요`:'이 곡은 슬롯 없이 원터치 10버튼만으로 완주할 수 있습니다'}</span></div>
        <div class="slot-board">${Array.from({length:Math.max(5,slots.length)},(_,i)=>i+1).map(n=>{const sl=slots.find(x=>x.slot===n);return `<div class="slot ${sl?'filled':''}"><div class="fret">${Array.from({length:5},(_,i)=>`<i></i>`).join('')}</div><div class="slot-no">S${n}</div><b>${sl?esc(sl.chord):'—'}</b><span>${sl?esc(sl.alt||''):'비어 있음'}</span></div>`;}).join('')}</div>
        ${slots.length?`<div class="slot-guide"><h4>이렇게 세팅하세요</h4><ol>${slots.map(sl=>`<li><b>S${sl.slot} · ${esc(sl.chord)}</b> <span class="tiny">(원곡 ${esc(sl.orig)})</span> ${sl.alt?`— 약식 대안: ${esc(sl.alt)}`:''}</li>`).join('')}</ol>
          <h4>교체 연습법</h4><p class="tiny">① 슬롯만 단독으로 4마디 반복(코드 잡기 확인) → ② 원터치 버튼 ↔ 슬롯 교차 8마디 → ③ 해당 마디만 30초 반복 → ④ 곡 전체를 70% 템포로. 슬롯에 넣은 코드가 손에 붙으면 같은 코드를 정식 운지로 바꿔 3단계로 넘어갑니다.</p></div>`:''}
        ${slotUse.length?`<div class="hint"><b>슬롯이 나오는 마디</b> · ${slotUse.slice(0,12).map(x=>`${esc(x.sec)} ${x.bar}마디 S${x.slot}(${esc(x.chord)})`).join(' · ')}${slotUse.length>12?' …':''}</div>`:''}
        <div class="hint" style="margin-top:10px"><b>등록할 때 확인할 것</b> · 슬롯에는 남자키 기준 코드 이름(예: Bm)을 등록하세요. 앱이 카포만큼 자동으로 이조하지 않는다면, 카포 수만큼 낮춘 이름(예: Capo 2에서 Bm → Am)을 등록하면 같은 소리가 납니다. 에어로밴드 공식 안내로는 SimplifyChord를 최대 12개(프렛마다 1개)까지 등록할 수 있어, 화면에 표시한 8칸을 넘겨도 됩니다.</div>
        <p class="tiny">원터치 버튼은 C·Dm·Em·F·G / Cm·D·E·Fm·Gm 10개입니다. 그 밖의 코드는 SimplifyChord 슬롯으로 옮깁니다.</p>`;
    }
    if(tab==='perc'){
      return `${head0}${tabs}
        <div class="two-col"><div class="card"><div class="eyebrow">STRUM</div><h3>오른손 스트로크</h3><div class="stroke-big">${esc(c.stroke||'↓ ↓↑ ↑↓↑').split(' ').map(x=>`<span>${esc(x)}</span>`).join('')}</div><p class="tiny">${esc(c.timeSignature)} · ${c.bpm}BPM 기준. 60BPM에서 4마디 정확히 친 뒤 5씩 올립니다.</p></div>
        <div class="card"><div class="eyebrow">PERCUSSIVE</div><h3>퍼커시브 포인트</h3><p>${esc(c.percussive||'2·4박에 손날로 바디를 톡 치는 것부터 시작합니다.')}</p></div></div>
        <div class="card" style="margin-top:12px"><h3>4단계로 만드는 퍼커시브</h3><div class="perc-steps">${[['① 컷','4박 뒤 손바닥으로 줄을 막았다 놓기. 60BPM 4마디'],['② 척킹(X)','2·4박에 손날로 줄만 막아 짧은 소리. 스트로크 사이에 넣기'],['③ 바디 톡','브릿지 옆을 엄지 옆면으로. 2·4박에만'],['④ 조합','Verse 컷 → Chorus 톡 → 마지막 마디 X']].map(([t,d])=>`<div><b>${t}</b><span>${esc(d)}</span></div>`).join('')}</div></div>
        <div class="hint">손목에 힘이 들어가면 소리가 죽습니다. 팔은 고정하고 손목만 돌린다는 느낌으로, 10분 이상 같은 동작을 붙잡지 마세요.</div>`;
    }
    const ev=c.evidence||[];
    return `${head0}${tabs}${partialStrip}
      <div class="card"><h3>확인한 값</h3><div class="kv"><div><span>원곡 키</span><b>${esc(c.originalKey)}</b></div><div><span>${c.maleShift ? `남자키(${c.maleShift}반음 ↓)` : '남자키(원키 그대로)'}</span><b>${esc(c.maleKey)}</b></div><div><span>AeroBand Capo</span><b>+${c.capo}</b></div><div><span>운지 폼</span><b>${esc(c.formText)}</b></div><div><span>박자</span><b>${esc(c.timeSignature)}</b><small>${esc(c.timeNote||'')}</small></div><div><span>BPM</span><b>${c.bpm||'—'}</b><small>${esc(c.bpmNote||'')}</small></div><div><span>원터치 매핑</span><b>${c.coverage.mapped}/${c.coverage.total}</b><small>슬롯 ${(c.slots||[]).length}개</small></div></div>
      <div class="divider"></div><h4>근거 자료</h4><ul class="ev">${ev.map(e=>`<li><a href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${esc(e.label)}</a><span class="tiny">${esc(e.note)}</span></li>`).join('')||'<li>근거 링크 없음</li>'}</ul>
      <p class="tiny">${esc(c.basis||'')} 남자키는 남성 원곡이면 원키 그대로(이조 0반음), 여성 원곡이면 −5반음으로 잡고, 그 목표 키를 AeroBand 원터치 10버튼(C·Dm·Em·F·G / Cm·D·E·Fm·Gm)에 맞추도록 카포를 골랐습니다. 에어로밴드 공식 안내에 따르면 CAPO+/CAPO− 버튼으로 조옮김하며 카포는 25키까지 지원됩니다(2026-11-22 확인).</p></div>`;
  }
  function chartModalShell(s){
    return `<div class="modal-layer" data-act="dismiss"><section class="modal chart-modal" role="dialog" aria-modal="true" aria-label="${esc(displayTitle(s))} 악보"><header class="modal-head"><div><div class="eyebrow">ONE-TOUCH CHART</div><h2>${esc(displayTitle(s))}</h2><div class="tiny">${esc(displayArtist(s))}${s.sourceIndices?.length?` · 원본 #${s.sourceIndices.join(', #')}`:''}</div></div><button class="icon-btn" aria-label="닫기" data-act="close">×</button></header>${chartModal(s)}</section></div>`;
  }

  function centerActiveNav(){try{if(!document.querySelector)return;const nav=document.querySelector('.nav');if(!nav)return;const btn=nav.querySelector('button.active');if(!btn)return;if(nav.scrollWidth<=nav.clientWidth+1)return;const n=nav.getBoundingClientRect(),b=btn.getBoundingClientRect();if(b.left>=n.left-1&&b.right<=n.right+1)return;const reduce=!!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);btn.scrollIntoView({inline:'center',block:'nearest',behavior:reduce?'auto':'smooth'});}catch{}}
  function render(){root.innerHTML=`<div class="shell">${bar()}<main>${({home,songs:songsPage,roadmap:roadmapPage,playlist:playlistPage,practice:practicePage,logs:logsPage,sources:sourcesPage,settings:settingsPage}[currentTab]||home)()}</main><footer class="footer">STRUM · PLAY A LITTLE. GO A LITTLE FURTHER. · 독립 백업/복원 버전</footer></div>${modal?renderModal():''}`;centerActiveNav();if(mini)setTimeout(syncMiniHeight,0);}
  function renderModal(){if(!modal)return '';if(modal.kind==='chart'){const s=song(modal.id);if(!s)return '';return chartModalShell(s);}let content='';let s=modal.id&&song(modal.id);
    if(modal.kind==='edit' || modal.kind==='new'){
      s=s||{id:'',title:'',artist:'',sourceIndices:[],verification:'added-by-user',videoUrl:'',audioUrl:'',mrUrl:'',key:'미확정',maleKey:'미확정',bpm:null,chords:'',chordStatus:'미확인',strumming:'',difficultyEasy:'미확인',difficultyStandard:'미확인',vocalDifficulty:'미확인',level:'미착수',tags:[],notes:'',setlist:false};
      content=`<form id="song-form" class="stack"><div class="field-grid"><div class="field"><label>곡 제목 *</label><input name="title" value="${esc(s.title)}" required maxlength="250" /></div><div class="field"><label>가수 *</label><input name="artist" value="${esc(s.artist)}" required maxlength="250" /></div><div class="field"><label>원본 영상 번호(여러 개면 쉼표)</label><input name="sourceIndices" value="${(s.sourceIndices||[]).join(', ')}" placeholder="6, 65" /></div><div class="field"><label>숙련도</label>${selectField('level',levels,s.level)}</div><div class="field"><label>원곡 키</label><input name="key" value="${esc(s.key)}" /></div><div class="field"><label>나에게 맞는 남자 키</label><input name="maleKey" value="${esc(s.maleKey)}" /></div><div class="field"><label>연습 BPM (확정값만)</label><input name="bpm" type="number" min="30" max="300" value="${s.bpm??''}" /></div><div class="field"><label>코드 검수 상태</label>${selectField('chordStatus',['미확인','자동분석 초안','웹 자료 검수 완료','부분 확인','청음 검수 완료'],s.chordStatus)}</div></div><div class="field"><label>코드 진행</label><input name="chords" value="${esc(s.chords)}" placeholder="예: G, Em, C, D" /></div><div class="field"><label>스트로크 메모</label><input name="strumming" value="${esc(s.strumming)}" /></div><div class="field-grid"><div class="field"><label>영상 보기 YouTube URL</label><input name="videoUrl" type="url" placeholder="https://www.youtube.com/watch?v=..." value="${esc(s.videoUrl)}" /></div><div class="field"><label>음악 직접 재생 URL (합법적 소유·사용 파일)</label><input name="audioUrl" type="url" placeholder="https://example.com/my-audio.mp3" value="${esc(s.audioUrl)}" /></div><div class="field"><label>MR(반주) YouTube URL</label><input name="mrUrl" type="url" placeholder="https://www.youtube.com/watch?v=..." value="${esc(s.mrUrl||'')}" /></div></div><div class="field"><label>메모 · 검수 근거 · 수정 이력</label><textarea name="notes">${esc(s.notes)}</textarea></div><label class="row"><input type="checkbox" name="setlist" ${s.setlist?'checked':''} /> 첫 버스킹 세트리스트에 포함하기</label><div class="row between"><div>${modal.kind==='edit'?action('delete-song:'+s.id,'곡 삭제','btn danger small'):''}</div><button class="btn primary" type="submit">곡 저장하기</button></div></form>`;
    }else if(modal.kind==='source'){
      const item=state.sources.find(v=>v.index===modal.index);content=`<form id="source-form" class="stack"><div class="field"><label>원본 영상 주소</label><input type="url" name="url" value="${esc(item.url)}" placeholder="https://www.youtube.com/watch?v=..." /></div><div class="field"><label>상태</label>${selectField('status',SOURCE_STATES,item.status)}</div><div class="field"><label>비고</label><textarea name="note">${esc(item.note)}</textarea></div><div class="hint">연결 곡: ${item.songs.map(id=>esc(song(id)?.title)).join(', ')||'없음'} · 곡 편집 화면에서 ‘원본 영상 번호’를 저장하면 이 표에 자동으로 연결됩니다.</div><button type="submit" class="btn primary">원본 번호 저장</button></form>`;
    }else if(modal.kind==='mr'){
      const q=mrSearch(s);content=`<div class="alert" style="margin-bottom:14px"><b>MR이 아직 등록되지 않았습니다.</b> 이 곡은 반주(MR·Inst·노래방) 영상이 확인되지 않아 비워 두었습니다. 아래 검색으로 찾아 주소를 붙여넣으면 이 곡의 <b>MR</b> 버튼과 미니 플레이어에 바로 연결됩니다.</div><div class="stack"><a class="btn primary" href="${esc(q)}" target="_blank" rel="noopener noreferrer">YouTube에서 '${esc(displayTitle(s))} ${esc(displayArtist(s))} MR' 검색 ↗</a><form id="mr-form" class="stack"><div class="field"><label>MR 영상 URL 붙여넣기</label><input name="mrUrl" type="url" required placeholder="https://www.youtube.com/watch?v=..." value="${esc(s.mrUrl||'')}" /></div><div class="hint">YouTube 주소만 확인합니다. 숨김 재생·음원 추출은 하지 않고, 저장한 영상은 하단 미니 플레이어에서 재생합니다.</div><button class="btn primary" type="submit">MR 저장하고 미니 플레이어로 재생</button></form></div>`;
    }else if(modal.kind==='video'){
      const video=ytId(s.videoUrl);const status=s.videoStatus||'';const unavailable=status.startsWith('영상 불가');
      content=video?`<div class="player"><iframe title="${esc(s.title)} 영상 보기" src="https://www.youtube-nocookie.com/embed/${video}?rel=0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div><p class="tiny" style="margin-top:11px">재생이 제한되면 YouTube에서 직접 보기를 이용하세요.</p>`:`<div class="empty"><strong>${unavailable?'원본 영상을 재생할 수 없습니다.':'저장된 영상 링크가 없습니다.'}</strong>${unavailable?esc(status)+' — 원본 영상이 삭제·비공개·채널 해지되어 사이트에서 재생할 수 없습니다. 아래 YouTube 검색으로 곡명을 확인하세요.':'영상이 아직 확인되지 않았습니다. 검색 후 정확한 유튜브 주소를 곡 편집 화면에 저장하면 여기서 바로 재생됩니다.'}</div>`;
      content+=`<div class="row" style="flex-wrap:wrap;margin-top:14px"><button class="btn primary" data-act="youtube-search:${s.id}">YouTube에서 영상 찾기 ↗</button>${video?`<button class="btn outline" data-act="youtube-open:${s.id}">YouTube 직접 보기</button>`:''}${action('edit:'+s.id,'영상 주소 수정','btn outline')}</div>`;
    }else if(modal.kind==='music'){
      let url=safeHttp(s.audioUrl);content=`<p class="tiny">음악 듣기는 소유하거나 이용 권한이 있는 MP3·오디오 URL 또는 휴대폰에 저장된 음원 파일로 재생합니다. YouTube 영상에서 음원을 무단 추출하거나 숨김 재생하지 않습니다.</p><div class="field" style="margin:13px 0"><label>휴대폰/PC에 저장한 오디오 파일 재생</label><input id="local-audio" type="file" class="input" accept="audio/*" /></div><div id="audio-mount">${url?`<audio class="audio-player" id="song-audio" controls preload="none" src="${esc(url)}"></audio>`:'<div class="hint">등록된 직접 재생용 음원 링크가 없습니다. 위에서 파일을 선택하거나 아래 버튼으로 음악 서비스를 이용하세요.</div>'}</div><div class="row" style="flex-wrap:wrap;margin-top:15px"><button class="btn primary" data-act="music-search:${s.id}">YouTube Music에서 찾기 ↗</button>${action('edit:'+s.id,'음원 URL 등록','btn outline')}</div>`;
    }
    return `<div class="modal-layer" data-act="dismiss"><section class="modal ${modal.kind==='edit'||modal.kind==='new'?'wide':''}" role="dialog" aria-modal="true" aria-label="${esc(s?.title||'편집')}"><header class="modal-head"><div><div class="eyebrow">${modal.kind==='music'?'AUDIO PLAYER':modal.kind==='video'?'WATCH VIDEO':modal.kind==='mr'?'MR REGISTER':'EDIT DATA'}</div><h2>${modal.kind==='new'?'새 곡 등록':modal.kind==='source'?'원본 #'+modal.index+' 수정':modal.kind==='mr'?'MR 등록 — '+esc(s?.title||''):esc(s?.title||'곡 수정')}</h2>${s?.artist?`<div class="tiny">${esc(s.artist)}</div>`:''}</div><button class="icon-btn" aria-label="닫기" data-act="close">×</button></header>${content}</section></div>`;
  }
  function setTab(n){if(!navs.some(([id])=>id===n))return;modal=null;currentTab=n;render();window.scrollTo({top:0,behavior:'auto'});}
  function mergeSeed(st){
    if(Number(st.seedVersion||0)>=SEED_VERSION) return false;
    const removed=new Set(st.removedSeedIds||[]);
    const ids=new Set(st.songs.map(s=>s.id));
    const pairs=new Set(st.songs.map(s=>norm(s.title)+'|'+norm(s.artist)));
    const urls=new Set(st.songs.map(s=>s.videoUrl).filter(Boolean));
    for(const seedSong of seed.songs){
      const cur=st.songs.find(s=>s.id===seedSong.id);
      if(cur){
        if(!cur.videoUrl && seedSong.videoUrl){cur.videoUrl=seedSong.videoUrl;cur.videoStatus=seedSong.videoStatus;}
        if(!cur.videoStatus && seedSong.videoStatus)cur.videoStatus=seedSong.videoStatus;
        /* MR 링크 병합: 비어 있으면 채우고, 사용자가 직접 넣은 값(mrEdited)은 건드리지 않는다 */
        if(seedSong.mrUrl&&!cur.mrEdited){for(const k of ['mrUrl','mrTitle','mrChannel','mrNote','mrSource'])cur[k]=seedSong[k];}
        else if(!cur.mrUrl && seedSong.mrUrl){for(const k of ['mrUrl','mrTitle','mrChannel','mrNote','mrSource'])cur[k]=seedSong[k];}
        /* MR 음원 파일(mrAudioUrl, 저장소 media/)도 같은 규칙으로 병합한다 */
        if(seedSong.mrAudioUrl&&!cur.mrEdited){for(const k of ['mrAudioUrl','mrTitle','mrNote','mrSource'])cur[k]=seedSong[k];}
        else if(!cur.mrAudioUrl && seedSong.mrAudioUrl){for(const k of ['mrAudioUrl','mrTitle','mrNote','mrSource'])cur[k]=seedSong[k];}
        if(Array.isArray(cur.sourceIndices)){
          if(!cur.sourceIndices.length && seedSong.sourceIndices.length)cur.sourceIndices=seedSong.sourceIndices.slice();
          else for(const n of seedSong.sourceIndices) if(!cur.sourceIndices.includes(n)) cur.sourceIndices.push(n);
        }
        /* 악보 병합: 사용자가 직접 고친 곡(chartEdited)은 그대로 두고, 나머지는 새 시드 악보로 갱신한다
           (2026-11-22 남자키 규칙 변경처럼 시드 계산 자체가 바뀐 경우에도 기존 기록·숙련도는 그대로 유지) */
        if(seedSong.chart && !cur.chartEdited) cur.chart=clone(seedSong.chart);
        else if(!cur.chart && seedSong.chart) cur.chart=clone(seedSong.chart);
        if(seedSong.chartStatus && !cur.chartEdited) cur.chartStatus=seedSong.chartStatus;
        /* 악보 설명(chartNote)도 시드가 갱신하면 함께 바꾼다. 사용자가 직접 고친 곡(chartEdited)은 그대로 둔다. */
        if(seedSong.chartNote && !cur.chartEdited) cur.chartNote=seedSong.chartNote;
        for(const k of ['category','workTitle','workArtist','categoryNote','playlistKind']){
          if(seedSong[k] && !cur[k]) cur[k]=seedSong[k];
        }
        if(seedSong.category) cur.category=seedSong.category;
        if(!cur.chartEdited){
          for(const k of ['key','maleKey','timeSignature','chordStatus','strumming','chords']){
            if(seedSong[k]) cur[k]=seedSong[k];
          }
          if(seedSong.bpm) cur.bpm=seedSong.bpm;
        }else{
          for(const k of ['key','maleKey','timeSignature','chordStatus','strumming','chords']){
            const empty=!cur[k] || ['미확정','미확인',''].includes(cur[k]);
            if(empty && seedSong[k]) cur[k]=seedSong[k];
          }
          if((cur.bpm==null||cur.bpm==='') && seedSong.bpm) cur.bpm=seedSong.bpm;
        }
        if(Array.isArray(cur.tags)&&Array.isArray(seedSong.tags)){
          for(const t of seedSong.tags) if(!cur.tags.includes(t)) cur.tags.push(t);
        }
        continue;
      }
      if(removed.has(seedSong.id)) continue;
      const key=norm(seedSong.title)+'|'+norm(seedSong.artist);
      if(pairs.has(key)) continue;
      if(seedSong.videoUrl && urls.has(seedSong.videoUrl)) continue;
      st.songs.push(clone(seedSong));ids.add(seedSong.id);pairs.add(key);if(seedSong.videoUrl)urls.add(seedSong.videoUrl);
    }
    for(const seedSource of seed.sources){
      const cur=st.sources.find(s=>s.index===seedSource.index);if(!cur)continue;
      if(seedSource.index===163)cur.status='제외';
      else if(!cur.url && cur.status==='미확인' && seedSource.status!=='미확인')cur.status=seedSource.status;
      if(!cur.url && seedSource.url)cur.url=seedSource.url;
      if(!cur.title && seedSource.title)cur.title=seedSource.title;
      if(!cur.channel && seedSource.channel)cur.channel=seedSource.channel;
      if(!cur.reason && seedSource.reason)cur.reason=seedSource.reason;
      if(!cur.note)cur.note=seedSource.note;
      else if(OLD_SEED_NOTES.has(cur.note))cur.note=seedSource.note;
    }
    st.seedVersion=SEED_VERSION;
    updateSongRecords(st);
    return true;
  }
  function updateSongRecords(st=state){for (const source of st.sources)source.songs=[];for(const s of st.songs){for(const i of (s.sourceIndices||[])){const r=st.sources[i-1];if(r && !r.songs.includes(s.id))r.songs.push(s.id);}}}
  function audioStop(){const el=get('song-audio');if(el)el.pause();if(trackObjectURL){URL.revokeObjectURL(trackObjectURL);trackObjectURL=null;}trackAudio=null;}
  /* ── 미니 플레이어 ────────────────────────────
     YouTube 정책: 영상을 숨기지 않는다. 도킹 바 안에 보이는 임베드 프레임을 두고
     접기(collapsed)도 프레임을 작게 유지한 채로만 줄인다(0×0 숨김 금지). */
  function ytEmbed(id){return `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0&playsinline=1&modestbranding=1`;}
  const mrSearch=s=>`https://www.youtube.com/results?search_query=${encodeURIComponent(displayTitle(s)+' '+displayArtist(s)+' MR inst')}`;
  function syncMiniHeight(){try{const el=get('mini-player');const h=el?Math.round(el.getBoundingClientRect().height||el.offsetHeight||0):0;if(document.documentElement?.style)document.documentElement.style.setProperty('--mini-h',h+'px');if(document.body?.style)document.body.style.paddingBottom=h?(h+10)+'px':'';}catch(err){}}
  function openMini(mode,s){
    if(!s)return;
    let kind=mode, url='';
    if(mode==='mr'){if(mrAudioOf(s))kind='mraudio';else url=s.mrUrl||'';}
    else if(mode==='music'){if(safeHttp(s.audioUrl))kind='audio';else url=s.videoUrl;}
    else {url=s.videoUrl;}
    if(kind==='audio'){if(!safeHttp(s.audioUrl)){notice('등록된 음원이 없어 영상으로 재생합니다.');kind='music';url=s.videoUrl;}}
    const isAudio=kind==='audio'||kind==='mraudio';
    const vid=isAudio?'':ytId(url);
    if(!isAudio&&!vid){notice(mode==='mr'?'MR 링크가 없습니다. MR 없음 버튼으로 등록할 수 있습니다.':'재생할 영상 링크가 없습니다.');return;}
    mini={kind:kind,songId:s.id,videoId:vid,audioUrl:kind==='audio'?safeHttp(s.audioUrl):kind==='mraudio'?mrAudioOf(s):'',title:displayTitle(s),sub:displayArtist(s),badge:mode==='mr'?'MR':mode==='music'?'음악':kind==='audio'?'음악':'영상',collapsed:false};
    renderMini();
    notice(mode==='mr'?`${s.title} · MR(반주)를 미니 플레이어에서 재생합니다.`:`${s.title} · ${mini.badge} 재생 중 — 악보로 이동해도 꺼지지 않습니다.`);
  }
  function closeMini(){try{get('mini-audio')?.pause();}catch(err){}if(trackObjectURL){URL.revokeObjectURL(trackObjectURL);trackObjectURL=null;}mini=null;renderMini();}
  function renderMini(){
    if(!miniRoot)return;
    if(!mini){miniRoot.innerHTML='';try{document.body.classList?.remove('has-mini');document.body.style.paddingBottom='';document.documentElement?.style&&document.documentElement.style.setProperty('--mini-h','0px');}catch(err){}return;}
    const s=song(mini.songId);
    const watch=s?((mini.kind==='mr'?s.mrUrl:s.videoUrl)||''):'';
    const isAudio=mini.kind==='audio'||mini.kind==='mraudio';
    const body=isAudio
      ?`<audio class="mini-audio" id="mini-audio" controls autoplay preload="none" src="${esc(mini.audioUrl)}"></audio>`
      :`<div class="mini-frame"><iframe src="${esc(ytEmbed(mini.videoId))}" title="${esc(mini.title)} ${esc(mini.badge)} 재생" allow="autoplay; encrypted-media; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>`;
    const link=mini.kind==='audio'?musicSearch(s||{title:mini.title,artist:mini.sub}):mini.kind==='mraudio'?esc(mini.audioUrl):esc(watch);
    const linkLabel=mini.kind==='mraudio'?'MR 음원 ↗':'YouTube ↗';
    miniRoot.innerHTML=`<section class="mini-player ${mini.collapsed?'collapsed':''}" id="mini-player" aria-label="하단 미니 플레이어">
      <div class="mini-info"><span class="mini-badge">${esc(mini.badge)}</span><div class="mini-text"><b>${esc(mini.title)}</b><span>${esc(mini.sub)}</span></div></div>
      ${body}
      <div class="mini-tools"><button type="button" class="mini-btn" data-act="mini-local" title="휴대폰에 저장한 오디오 파일 재생">내 파일</button><a class="mini-btn" href="${link}" target="_blank" rel="noopener noreferrer">${linkLabel}</a><button type="button" class="mini-btn" data-act="mini-collapse" aria-label="${mini.collapsed?'펼치기':'접기'}" title="${mini.collapsed?'펼치기':'접기'}">${mini.collapsed?'▴':'▾'}</button><button type="button" class="mini-btn mini-close" data-act="mini-close" aria-label="미니 플레이어 닫기" title="닫기">×</button></div>
      <input id="mini-file" type="file" accept="audio/*" class="hide" />
    </section>`;
    try{document.body.classList?.add('has-mini');}catch(err){}
    syncMiniHeight();
  }
  function closeModal(){audioStop();modal=null;render();}
  function editSong(id){modal={kind:id?'edit':'new',id};render();}
  function setSettingsField(name,value){state.settings[name]=value;save();render();}
  function changeBpm(amount){state.settings.bpm=Math.max(40,Math.min(180,state.settings.bpm+amount));save();if(metronome){stopMetro();startMetro();}render();}
  function metroBeep(accent=false){try{const ctx=metronome.ctx,osc=ctx.createOscillator(),gain=ctx.createGain(),now=ctx.currentTime;osc.type='sine';osc.frequency.setValueAtTime(accent?1000:760,now);gain.gain.setValueAtTime(.001,now);gain.gain.exponentialRampToValueAtTime(accent?.24:.13,now+.008);gain.gain.exponentialRampToValueAtTime(.001,now+.07);osc.connect(gain);gain.connect(ctx.destination);osc.start(now);osc.stop(now+.08);}catch(e){stopMetro();notice('메트로놈 오디오를 사용할 수 없습니다.');}}
  function paintBeat(beat){try{const dots=get('beat-dots');if(!dots)return;const list=[...dots.children];list.forEach((el,i)=>el.classList.toggle('now',i===beat));}catch{}}
  function startMetro(){const A=window.AudioContext||window.webkitAudioContext;if(!A){notice('이 브라우저는 오디오 타이밍을 지원하지 않습니다.');return;}const ctx=new A();const beats=beatCount(state.settings.timeSignature);metronome={ctx,beat:0,beats};metroBeep(true);paintBeat(0);bpmTimer=setInterval(()=>{if(!metronome)return;metronome.beat=(metronome.beat+1)%metronome.beats;const acc=metronome.beat===0||(metronome.beats===6&&metronome.beat===3);metroBeep(acc);paintBeat(metronome.beat);},60000/state.settings.bpm);render();}
  function stopMetro(){clearInterval(bpmTimer);bpmTimer=null;metronome?.ctx?.close();metronome=null;}
  function timerTick(){if(!sessionRunning)return;let now=Date.now();let passed=Math.floor((now-lastTime)/1000);if(passed<=0)return;lastTime+=passed*1000;remaining=Math.max(0,remaining-passed);const display=get('timer-display');if(display)display.textContent=mins(remaining);if(remaining===0){sessionRunning=false;clearInterval(practiceInterval);practiceInterval=null;notice('연습 시간이 끝났습니다! 기록을 저장하세요.');render();}}
  function toggleTimer(){sessionRunning=!sessionRunning;if(sessionRunning){lastTime=Date.now();practiceInterval=setInterval(timerTick,250);}else{clearInterval(practiceInterval);practiceInterval=null;}render();}
  function resetTimer(){sessionRunning=false;clearInterval(practiceInterval);practiceInterval=null;remaining=state.settings.minutes*60;render();}
  function download(name,textData,type){const blob=new Blob([textData],{type:type||'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  const csvEscape=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
  function exportCsv(records,columns,name){const rows=[columns.join(','),...records.map(r=>columns.map(c=>csvEscape(r[c])).join(','))];download(name,'\uFEFF'+rows.join('\r\n'),'text/csv;charset=utf-8');}
  function parseCsv(t){const data=[];let row=[],field='',quoted=false;for(let i=0;i<t.length;i++){let c=t[i];if(quoted){if(c==='"'&&t[i+1]==='"'){field+='"';i++;}else if(c==='"')quoted=false;else field+=c;}else if(c==='"')quoted=true;else if(c===','){row.push(field);field='';}else if(c==='\n'){row.push(field.replace(/\r$/,''));data.push(row);row=[];field='';}else field+=c;}if(row.length||field) {row.push(field);data.push(row);}const header=(data.shift()||[]).map(s=>s.replace(/^\uFEFF/,'').trim());return data.filter(x=>x.some(v=>v.trim())).map(row=>Object.fromEntries(header.map((h,i)=>[h,row[i]||''])));}
  const csvRows=() => state.songs.map(s=>({id:s.id,title:s.title,artist:s.artist,sourceIndices:(s.sourceIndices||[]).join('|'),verification:s.verification,videoUrl:s.videoUrl,videoStatus:s.videoStatus||'',audioUrl:s.audioUrl,key:s.key,maleKey:s.maleKey,bpm:s.bpm||'',timeSignature:(s.chart&&s.chart.timeSignature)||s.timeSignature||'',capo:(s.chart&&Number.isFinite(s.chart.capo))?s.chart.capo:'',chords:s.chords,chordStatus:s.chordStatus,strumming:s.strumming,level:s.level,notes:s.notes,setlist:s.setlist?'true':'false'}));
  const chartRows=() => state.songs.filter(s=>chartOf(s)).map(s=>{const c=chartOf(s);return {id:s.id,title:s.title,artist:s.artist,originalKey:c.originalKey,maleKey:c.maleKey,shift:c.maleShift,capo:c.capo,form:c.formText,timeSignature:c.timeSignature,bpm:c.bpm,stage:c.stage,slots:(c.slots||[]).map(x=>x.slot+':'+x.chord).join('|'),mapped:c.coverage.mapped+'/'+c.coverage.total,stroke:c.stroke};});
  const sourceRows=()=>state.sources.map(s=>({index:s.index,status:s.status,url:s.url,title:s.title||'',channel:s.channel||'',reason:s.reason||'',note:s.note,songIds:s.songs.join('|')}));
  function mergedSongs(incoming){let updated=0,added=0;for(const o of incoming){if(!o||!String(o.title||'').trim()||!String(o.artist||'').trim())continue;let id=String(o.id||'').trim(),ex=state.songs.find(s=>s.id===id)||state.songs.find(s=>norm(s.title)===norm(o.title)&&norm(s.artist)===norm(o.artist));let base=ex||{...clone(seed.songs.at(-1)),id:uniqueId(),sourceIndices:[],level:'미착수',verification:'imported',tags:[],notes:'',setlist:false};let indices=Array.isArray(o.sourceIndices)?o.sourceIndices:String(o.sourceIndices||'').split(/[|,]/).map(v=>+v.trim()).filter(n=>n>=1&&n<=211);let filled=Object.fromEntries(Object.entries(o).filter(([k,v])=>v!==''&&v!==null&&v!==undefined));let record={...base,...filled,id:ex?.id||id||base.id,title:String(o.title).trim(),artist:String(o.artist).trim(),sourceIndices:o.sourceIndices!==undefined&&String(o.sourceIndices)!==''?indices:base.sourceIndices,level:LEVELS.includes(o.level)?o.level:base.level,setlist:typeof o.setlist==='boolean'?o.setlist:(o.setlist==='true'?true:o.setlist==='false'?false:base.setlist),tags:Array.isArray(o.tags)?o.tags:base.tags};if(ex){Object.assign(ex,record);updated++;}else{state.songs.push(record);added++;}}
    updateSongRecords();return {updated,added};}
  function importJson(parsed,mode){if(Array.isArray(parsed))return mergedSongs(parsed);if(!parsed||!Array.isArray(parsed.songs))throw new Error('songs 배열이 있는 JSON이어야 합니다.');
    if(mode==='replace'){
      if(!Array.isArray(parsed.sources) || !Array.isArray(parsed.logs))throw new Error('전체 교체는 sources와 logs를 포함한 STRUM 백업 JSON만 가능합니다.');
      if(parsed.sources.length!==211||parsed.sources.some((s,i)=>s.index!==i+1)||!parsed.songs.every(s=>s&&typeof s.id==='string'&&typeof s.title==='string'&&typeof s.artist==='string'&&typeof s.verification==='string'&&Array.isArray(s.sourceIndices)))throw new Error('원본 번호 또는 곡 구조가 올바르지 않습니다. 병합을 권장합니다.');
      if(parsed.sources[162].status!=='제외')throw new Error('원본 #163의 제외 상태가 보존되지 않았습니다. 전체 교체 중단.');
      state={...defaultState(),...parsed,settings:{...defaultState().settings,...(parsed.settings||{})}};
      updateSongRecords();return {updated:state.songs.length,added:0};
    }
    const res=mergedSongs(parsed.songs);
    if(Array.isArray(parsed.sources)){for(const s of parsed.sources){let ex=state.sources.find(r=>r.index===+s.index);if(ex){if(s.url)ex.url=s.url;if(s.note)ex.note=s.note;if(s.title)ex.title=s.title;if(s.channel)ex.channel=s.channel;if(s.reason)ex.reason=s.reason;if(SOURCE_STATES.includes(s.status)&&ex.index!==163)ex.status=s.status;else if(ex.index===163)ex.status='제외';}}}
    if(Array.isArray(parsed.logs)){const ids=new Set(state.logs.map(l=>l.id));for(const l of parsed.logs){if(l.id&&!ids.has(l.id)){state.logs.push(l);ids.add(l.id);}}}
    updateSongRecords();return res;
  }
  async function importFile(){const file=get('import-file')?.files?.[0],mode=get('import-mode')?.value||'merge';if(!file){notice('가져올 JSON 또는 CSV를 선택하세요.');return;}if(mode==='replace'){if(file.name.toLowerCase().endsWith('.csv')){notice('전체 교체는 JSON 백업만 가능합니다. CSV는 병합으로 가져오세요.');return;}if(!confirm('현재 데이터를 백업 다운로드한 후 전체 교체합니다. 계속할까요?'))return;download('STRUM_before_replace_'+dateKey()+'.json',JSON.stringify(state,null,2),'application/json;charset=utf-8');}
    try{const text=await file.text();let parsed=file.name.toLowerCase().endsWith('.csv')?parseCsv(text):JSON.parse(text);if(file.name.toLowerCase().endsWith('.csv')&&parsed.some(r=>r.index&&!r.title))throw new Error('원본 영상 CSV는 곡 CSV와 형식이 달라 이 화면에서 가져올 수 없습니다. 전체 JSON 백업을 이용하세요.');let res=importJson(parsed,mode);save();render();notice(`가져오기 완료: 신규 ${res.added}곡, 갱신 ${res.updated}곡`);}catch(e){notice('가져오기 실패: '+e.message);}
  }
  function saveSongForm(form){let values=Object.fromEntries(new FormData(form));let title=String(values.title||'').trim(),artist=String(values.artist||'').trim();if(!title||!artist){notice('제목과 가수를 입력하세요.');return;}let s=modal.id? song(modal.id):null;
    const prev=s?{key:s.key,maleKey:s.maleKey,chords:s.chords,strumming:s.strumming,bpm:s.bpm,mrUrl:s.mrUrl||''}:null;
    let nums=String(values.sourceIndices||'').split(',').map(n=>+n.trim()).filter(i=>Number.isInteger(i)&&i>=1&&i<=211);
    if(!s){s={...clone(seed.songs.at(-1)),id:uniqueId(),verification:'added-by-user',tags:[]};state.songs.push(s);}Object.assign(s,{title,artist,sourceIndices:[...new Set(nums)],level:values.level,videoUrl:safeHttp(values.videoUrl)||'',audioUrl:safeHttp(values.audioUrl)||'',mrUrl:(safeHttp(values.mrUrl)?('https://www.youtube.com/watch?v='+(ytId(values.mrUrl)||'')):''),key:values.key||'미확정',maleKey:values.maleKey||'미확정',bpm:values.bpm?+values.bpm:null,chords:values.chords||'',chordStatus:values.chordStatus,strumming:values.strumming||'',notes:values.notes||'',setlist:form.querySelector('[name="setlist"]')?.checked||false});if(prev&&s.chart&&(prev.key!==s.key||prev.maleKey!==s.maleKey||prev.chords!==s.chords||prev.strumming!==s.strumming||prev.bpm!==s.bpm))s.chartEdited=true;if(prev&&prev.mrUrl!==(s.mrUrl||'')){s.mrEdited=true;s.mrTitle='';s.mrChannel='';s.mrNote='직접 등록('+dateKey()+')';s.mrSource='user';}updateSongRecords();save();modal=null;render();notice('곡 정보가 저장되었습니다.');}
  function saveSourceForm(form){let ex=state.sources.find(s=>s.index===modal.index),data=new FormData(form);ex.url=safeHttp(data.get('url'));ex.status=ex.index===163?'제외':(SOURCE_STATES.includes(data.get('status'))?data.get('status'):'미확인');ex.note=String(data.get('note')||'');save();modal=null;render();notice('원본 영상 정보를 저장했습니다.');}
  function saveMrForm(form){
    const s=modal&&modal.id?song(modal.id):null;if(!s){notice('곡을 찾을 수 없습니다.');return;}
    const vid=ytId(new FormData(form).get('mrUrl'));
    if(!vid){notice('YouTube 영상 주소를 확인하세요. 예: https://www.youtube.com/watch?v=...');return;}
    s.mrUrl='https://www.youtube.com/watch?v='+vid;s.mrEdited=true;s.mrTitle='';s.mrChannel='';s.mrNote='직접 등록('+dateKey()+')';s.mrSource='user';
    const back=modal.from;save();modal=null;render();
    if(back==='chart'){modal={kind:'chart',id:s.id,tab:'chart'};render();}
    openMini('mr',s);notice('MR을 저장했습니다. 미니 플레이어에서 재생합니다.');
  }
  function saveLogForm(form){const d=new FormData(form);const m=Math.max(1,Math.min(480,+d.get('minutes')||0));state.logs.push({id:'log-'+Date.now()+'-'+Math.random().toString(36).slice(2,5),date:dateKey(),minutes:m,songId:d.get('songId')||'',mode:state.settings.mode,chords:String(d.get('chords')||''),strum:String(d.get('strum')||''),memo:String(d.get('memo')||'')});if(d.get('songId')){let s=song(d.get('songId'));if(s&&s.level==='미착수')s.level='연습 중';}state.completedStages=[];save();resetTimer();notice('오늘 연습 기록을 저장했습니다.');}
  function handleAction(act){let [cmd,...rest]=act.split(':'),value=rest.join(':');switch(cmd){
    case 'start-practice':case 'go-practice':setTab('practice');return;
    case 'go-songs':setTab('songs');return;
    case 'filter-cat':statusFilter=value;setTab('songs');return;
    case 'go-roadmap':setTab('roadmap');return;
    case 'go-playlist':setTab('playlist');return;
    case 'go-sources':setTab('sources');return;
    case 'new-song':editSong(null);return;
    case 'edit':editSong(value);return;
    case 'chart':modal={kind:'chart',id:value,tab:'chart'};render();return;
    case 'chart-tab':if(modal){modal.tab=value;render();}return;
    case 'metro-song':{const s=song(value),c=s&&chartOf(s);if(c){state.settings.bpm=Math.max(40,Math.min(180,Math.round(c.bpm||state.settings.bpm)));state.settings.timeSignature=c.timeSignature||state.settings.timeSignature;state.settings.focusSongId=s.id;save();if(metronome){stopMetro();}modal=null;setTab('practice');notice(`${s.title} · ${state.settings.bpm}BPM · ${state.settings.timeSignature} 메트로놈으로 연습을 준비했습니다.`);}else notice('이 곡은 아직 악보 검수 대기입니다.');return;}
    case 'video':case 'music':{const s=song(value);if(!s)return;if(cmd==='music'&&!safeHttp(s.audioUrl)&&!s.videoUrl){audioStop();modal={kind:'music',id:value};render();return;}openMini(cmd,s);return;}
    case 'mr':{const s=song(value);if(!s)return;if(hasMr(s)){openMini('mr',s);return;}modal={kind:'mr',id:value,from:modal&&modal.kind==='chart'?'chart':''};render();return;}
    case 'mini-close':closeMini();return;
    case 'mini-collapse':if(mini){mini.collapsed=!mini.collapsed;renderMini();}return;
    case 'mini-local':get('mini-file')?.click();return;
    case 'close':case 'dismiss':closeModal();return;
    case 'source':modal={kind:'source',index:+value};render();return;
    case 'youtube-search':{const s=song(value);if(s)openTab(youtubeSearch(s));return;}
    case 'youtube-open':{const s=song(value);if(s){const idx=ytId(s.videoUrl);openTab(idx?'https://www.youtube.com/watch?v='+idx:youtubeSearch(s));}return;}
    case 'music-search':{const s=song(value);if(s)openTab(musicSearch(s));return;}
    case 'mode':setSettingsField('mode',value);return;
    case 'ts':state.settings.timeSignature=value;save();if(metronome){stopMetro();startMetro();}else render();return;
    case 'minutes':resetTimer();setSettingsField('minutes',+value);remaining=+value*60;render();return;
    case 'timer-toggle':toggleTimer();return;
    case 'timer-reset':resetTimer();return;
    case 'metro-toggle':metronome?stopMetro():startMetro();render();return;
    case 'bpm-up':changeBpm(5);return;
    case 'bpm-down':changeBpm(-5);return;
    case 'more-sources':showAllSources=true;render();return;
    case 'export-json':download('STRUM_full_backup_'+dateKey()+'.json',JSON.stringify(state,null,2),'application/json;charset=utf-8');notice('전체 백업 파일을 생성했습니다.');return;
    case 'export-csv':exportCsv(csvRows(),['id','title','artist','sourceIndices','verification','videoUrl','videoStatus','audioUrl','key','maleKey','bpm','timeSignature','capo','chords','chordStatus','strumming','level','notes','setlist'],'STRUM_songs_'+dateKey()+'.csv');return;
    case 'export-charts':exportCsv(chartRows(),['id','title','artist','originalKey','maleKey','shift','capo','form','timeSignature','bpm','stage','slots','mapped','stroke'],'STRUM_charts_'+dateKey()+'.csv');return;
    case 'export-sources':exportCsv(sourceRows(),['index','status','url','title','channel','reason','note','songIds'],'STRUM_211_sources_'+dateKey()+'.csv');return;
    case 'import-file':importFile();return;
    case 'delete-song':if(confirm('이 곡을 목록에서 삭제할까요? 기존 연습 기록은 유지됩니다.')){state.songs=state.songs.filter(s=>s.id!==value);if(/^(verified|playlist|restored)-/.test(value))state.removedSeedIds=[...new Set([...(state.removedSeedIds||[]),value])];updateSongRecords();save();modal=null;render();notice('삭제했습니다.');}return;
    case 'delete-log':if(confirm('이 연습 기록을 삭제할까요?')){state.logs=state.logs.filter(l=>l.id!==value);save();render();}return;
    case 'clear-data':if(confirm('현재 브라우저 데이터를 초기화합니다. 먼저 자동 백업 파일을 다운로드합니다. 계속할까요?')&&confirm('최종 확인: 복원본 기본 데이터로 되돌릴까요?')){download('STRUM_before_reset_'+dateKey()+'.json',JSON.stringify(state,null,2),'application/json;charset=utf-8');state=defaultState();save();resetTimer();render();notice('초기화했습니다.');}return;
  }}
  document.addEventListener('click',e=>{const nav=e.target.closest('[data-nav]');if(nav){e.preventDefault();setTab(nav.dataset.nav);return;}const button=e.target.closest('[data-act]');if(!button)return;if(button.dataset.act==='dismiss'){if(e.target!==button)return;e.preventDefault();closeModal();return;}e.preventDefault();handleAction(button.dataset.act);});
  document.addEventListener('submit',e=>{if(e.target.id==='song-form'){e.preventDefault();saveSongForm(e.target);}else if(e.target.id==='source-form'){e.preventDefault();saveSourceForm(e.target);}else if(e.target.id==='practice-form'){e.preventDefault();saveLogForm(e.target);}else if(e.target.id==='mr-form'){e.preventDefault();saveMrForm(e.target);}});
  document.addEventListener('input',e=>{
    if(e.target.id==='song-search'){searchQuery=e.target.value;const filtered=filterSongs();const list=get('song-list');if(list)list.innerHTML=filtered.length?filtered.map(songRow).join(''):'<div class="empty">검색된 곡이 없습니다.</div>';const count=get('song-result-count');if(count)count.textContent='검색 결과 '+filtered.length+'곡 · 데이터가 추가되면 즉시 반영됩니다.';return;}
    if(e.target.id==='source-search'){sourceQuery=e.target.value;render();get('source-search')?.focus();try{get('source-search').setSelectionRange(sourceQuery.length,sourceQuery.length);}catch{}return;}
    if(e.target.id==='bpm-range'){const bpm=+e.target.value;if(bpm!==state.settings.bpm){state.settings.bpm=bpm;save();if(metronome){stopMetro();startMetro();}else {const l=get('bpm-label');if(l)l.textContent=bpm+' BPM';}}return;}
    if(e.target.id==='local-audio'){const file=e.target.files?.[0];if(!file)return;if(!file.type.startsWith('audio/')){notice('오디오 파일을 선택하세요.');return;}audioStop();trackObjectURL=URL.createObjectURL(file);let mount=get('audio-mount');if(mount){mount.innerHTML='<audio class="audio-player" id="song-audio" controls autoplay></audio>';trackAudio=get('song-audio');trackAudio.src=trackObjectURL;trackAudio.play().catch(()=>{});}return;}
    if(e.target.id==='mini-file'){const file=e.target.files?.[0];if(!file)return;if(!file.type.startsWith('audio/')){notice('오디오 파일을 선택하세요.');return;}if(trackObjectURL)URL.revokeObjectURL(trackObjectURL);trackObjectURL=URL.createObjectURL(file);mini={kind:'audio',songId:mini?.songId||'',videoId:'',audioUrl:trackObjectURL,title:file.name,sub:'내 오디오 파일',badge:'내 파일',collapsed:false};renderMini();return;}
  });
  document.addEventListener('change',e=>{
    if(e.target.dataset.step!==undefined){let i=+e.target.dataset.step;if(e.target.checked&&!state.completedStages.includes(i))state.completedStages.push(i);else if(!e.target.checked)state.completedStages=state.completedStages.filter(v=>v!==i);save();const checked=state.completedStages.length;let pill=e.target.closest('.card')?.querySelector('.pill');if(pill)pill.textContent=checked+'/5 완료';return;}
    if(e.target.id==='song-filter'){statusFilter=e.target.value;render();return;}
    if(e.target.id==='source-filter'){sourceFilter=e.target.value;showAllSources=false;render();return;}
    if(e.target.id==='weekly-goal'){state.settings.weeklyGoal=+e.target.value;save();notice('주간 목표 변경됨.');return;}
    if(e.target.name==='mode'&&currentTab==='settings'){state.settings.mode=e.target.value;save();return;}
    if(e.target.name==='ts'&&currentTab==='settings'){state.settings.timeSignature=e.target.value;save();if(metronome){stopMetro();startMetro();}else render();return;}
  });
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&modal)closeModal();});
  window.addEventListener('resize',()=>{if(mini)syncMiniHeight();});
  window.addEventListener('beforeunload',()=>{stopMetro();});
  render();
})();
