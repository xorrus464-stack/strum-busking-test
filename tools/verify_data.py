import json,pathlib
b=pathlib.Path(__file__).resolve().parents[1]
songs=json.loads((b/'data'/'songs.seed.json').read_text())
src=json.loads((b/'data'/'source-videos.seed.json').read_text())
assert len(src)==211
assert [r['index'] for r in src]==list(range(1,212))
assert len({s['id'] for s in songs})==len(songs)
assert len([s for s in songs if s['verification'] != 'learning-recommendation-not-in-original-playlist'])==25
for s in songs:
 for n in s['sourceIndices']:
  assert 1<=n<=211 and s['id'] in src[n-1]['songs']
assert len(src[5]['songs'])==7
assert len(src[64]['songs'])==2
assert src[162]['status']=='제외'
assert src[161]['status']=='미확인'
print('OK: source 211, originals 25, recommended 1, #6→7 songs, #65→2 songs, #163 excluded')

assert len([s for s in songs if s['verification']=='user-title-only'])==1
assert src[171]['songs'] and src[196]['songs'] and src[200]['songs'] and src[202]['songs'] and src[210]['songs']
assert not any(s['sourceIndices'] for s in songs if s['verification'].startswith('learning-'))
print('OK: user corrected #172/#197/#201/#203/#211; artist unknown labeled; extras separate')
