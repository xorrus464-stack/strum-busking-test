import json, pathlib, csv
base=pathlib.Path(__file__).resolve().parents[1]
records = [
('오늘','오왠 (O.WHEN)',None,'site-top3'),
('민들레','우효 (OOHYO)',None,'site-top3'),
('Thank You','Dido',None,'site-top3'),
('Ten Thousand Hours','Macklemore & Ryan Lewis',2,'user-verified'),
('추억이면','부활',6,'user-verified'),
('희재','성시경',6,'user-verified'),
('한숨','이하이',6,'user-verified'),
('내가 너의 곁에 잠시 살았다는 걸','토이',6,'user-verified'),
('예뻤어','DAY6',6,'user-verified'),
('도망가자','선우정아',6,'user-verified'),
('청혼','노을',6,'user-verified'),
('TOMBOY','혁오',20,'user-verified'),
('Flower','오반',65,'user-verified'),
('死別 (feat. GUMI)','Shannon',65,'user-verified'),
('Englishman in New York','Sting',70,'user-verified'),
('How To Cry','Sam Smith',74,'user-verified'),
('나는 버려질 장난감','아소 · 아날로그소년',108,'user-verified'),
('たぶん (아마도)','YOASOBI',109,'user-verified'),
('생각을 멈추다 보면','최유리',165,'user-verified'),
('오르막길','윤종신',169,'user-verified'),
('날씨가 좋고 바람도 좋아','가수 미확인',172,'user-title-only'),
('세상이 그대를 속일지라도','김장훈',197,'user-verified'),
('사랑한 마음엔 죄가 없다','소란',201,'user-verified'),
('닮은사람','이기찬',203,'user-verified'),
('히로인','back number',211,'user-verified'),
]
songs=[]
for i,(title,artist,idx,evidence) in enumerate(records,1):
  songs.append({'id':f'verified-{i:03}', 'title':title, 'artist':artist, 'sourceIndices':([] if idx is None else [idx]),'verification':evidence,'videoUrl':'','audioUrl':'','key':'미확정','maleKey':'미확정','bpm':None,'chords':'','chordStatus':'미확인','strumming':'','difficultyEasy':'미확인','difficultyStandard':'미확인','vocalDifficulty':'미확인','level':'미착수','tags':(['입문 후보'] if i<=3 else []),'notes':('가수 및 정확한 영상·코드 미확인' if evidence=='user-title-only' else ''),'setlist':False})
songs.append({'id':'suggested-stand-by-me','title':'Stand by Me','artist':'Ben E. King','sourceIndices':[],'verification':'learning-recommendation-not-in-original-playlist','videoUrl':'','audioUrl':'','key':'미확정','maleKey':'미확정','bpm':None,'chords':'','chordStatus':'미확인','strumming':'','difficultyEasy':'입문','difficultyStandard':'초급','vocalDifficulty':'미확인','level':'미착수','tags':['연습 추천곡'],'notes':'추천 학습곡이며 원래 152곡에 포함되었는지는 확인되지 않음','setlist':False})
for s in songs:
  if s['title']=='나는 버려질 장난감':s['notes']='과거 자동분석 코드 후보: Db → F계열 → Bbm → Gb → Gbm. 청음 검수 미완료. 확정 코드로 사용 금지.'
raw=[{'index':i,'status':('제외' if i==163 else '미확인'),'url':'','note':'','songs':[s['id'] for s in songs if i in s['sourceIndices']]} for i in range(1,212)]
for entry in raw:
    if entry['index']==6: entry['note']='확인된 7곡을 각각 분리 관리'
    if entry['index']==65: entry['note']='확인된 2곡을 각각 분리 관리'
    if entry['index']==163: entry['note']='이전 요청에 따라 선별 목록에서 제외'
metadata={'originalPlaylist':'https://www.youtube.com/playlist?list=PLdOy20BJp9XElDHDvAJI6mUG48BmfDX-y','playlistId':'PLdOy20BJp9XElDHDvAJI6mUG48BmfDX-y','fullyNamedSongCount':24,'partialNamedSongCount':1,'additionalRecommendedSongCount':1,'title':'STRUM · 나의 버스킹 여정','reconstruction':True,'originalSite':'https://aeroband-busking-jc.actualtide8.chatgpt.site/', 'originalVideoCount':211,'originalReportedCuratedSongCount':152,'reportedInaccessibleVideoCount':42,'recoveredOriginalSongCount':len(records),'sourceDisclosure':'원본 152곡 데이터 미확보. 25개 항목(가수 미확인 1개) + 추천 1곡만 입력. 211개 번호 슬롯은 영상 URL이 확인된 것이 아님.'}
for name,obj in [('songs.seed.json',songs),('source-videos.seed.json',raw),('metadata.json',metadata)]:
 (base/'data'/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# App loads JS globals, no server needed
def write_js(path,variable,obj):
 (base/'src'/path).write_text(f'window.{variable} = '+json.dumps(obj,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
write_js('seed.js','STRUM_SEED',{'songs':songs,'sources':raw,'meta':metadata})
print('songs',len(songs),'originals',len(records),'sources',len(raw))

# Keep CSV exports consistent with generated seed. This script resets the demo seed to the
# 25 documented records, NOT the user's live browser data or future complete 152-song import.
cols=['id','title','artist','sourceIndices','verification','videoUrl','audioUrl','key','maleKey','bpm','chords','chordStatus','strumming','level','notes','setlist']
with (base/'data'/'songs.verified.csv').open('w', encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
  for s in songs:
    if s['verification'].startswith('learning-'):continue
    row={c:s.get(c,'') for c in cols};row['sourceIndices']='|'.join(map(str,s['sourceIndices']));row['setlist']=str(row['setlist']).lower();w.writerow(row)
with (base/'data'/'source-videos.slots.csv').open('w', encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['index','status','url','note','songIds'])
  for v in raw:w.writerow([v['index'],v['status'],v['url'],v['note'],'|'.join(v['songs'])])
