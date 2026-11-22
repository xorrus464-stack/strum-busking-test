"""곡별 실측 자료(원키·박자·BPM·코드 진행·근거 URL).

여기 적힌 값은 2026-11-22 웹 검색으로 확인한 코드표/악보 메타데이터에서 옮긴 것이다.
- `sections`: 원곡 키 기준 코드 순서. 한 항목이 한 마디이며, 마디 안에 코드가 2개면 2박씩 바뀐다.
  코드표의 순서를 4박 마디 카드로 정리한 '연습용 배치'이며, 원곡의 세부 마디 배치와 다를 수 있다.
- `shift`: 원곡 키에서 남자키로 내리는 반음 수(2 = 온음 2개). 여성 보컬 원곡은 4, 남성 원곡은 2를 기본값으로 두고
  원터치 버튼에 더 잘 들어가는 값을 ±1 안에서 고른다.
- `stage`: 1(원터치+기본 스트로크) ~ 4(퍼커시브 버스킹).
"""

# sections: [{name, bars: [[코드,...], ...]}]
CHARTS = {
    # ── 사용자 확인 25곡 ──────────────────────────────────────────
    "verified-001": {  # 오늘 / 오왠
        "originalKey": "E", "timeSignature": "4/4", "timeNote": "khmerchords 코드표 표기",
        "bpm": 70, "shift": 2, "bpmNote": "khmerchords 70bpm",
        "stage": 3,
        "sections": [
            {"name": "Intro", "bars": [["E", "Am"], ["A", "E"]]},
            {"name": "Verse", "bars": [["Am"], ["E"], ["C#m"], ["F#"], ["F#m"], ["B"]]},
            {"name": "Pre", "bars": [["E"], ["G#"], ["C#m"], ["A"], ["F#m"]]},
            {"name": "Chorus", "bars": [["E"], ["G#"], ["C#m"], ["F#"], ["F#m"], ["B"]]},
            {"name": "Bridge", "bars": [["C#m"], ["B"], ["A"], ["E"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (한 마디에 코드 하나, 8분 중심)",
        "percussive": "후렴 마지막 마디만 2·4박에 오른손 손날로 바디를 톡 쳐(X) 박자를 살린다.",
        "why": "F#·G#·C#m이 섞여 초반에는 손이 바빠지는 곡. 원터치+슬롯으로 먼저 귀를 잡고 3단계에서 정식 코드로.",
        "evidence": [
            ("khmercords 코드표", "https://www.khmerchords.com/en/owhen/today", "Time 4/4 · Tempo 70bpm · 코드 E G# C#m F# A(add9) B7 F#m"),
            ("코드악보 PDF(원키 E)", "https://patross0303.com/wp-content/uploads/2023/07/%EC%98%A4%EC%99%A0-%EC%98%A4%EB%8A%98-%EC%BD%94%EB%93%9C%EC%95%85%EB%B3%B4-1.pdf", "원키 E Key, 마디별 코드"),
        ],
    },
    "verified-002": {
        "percussiveReady": True,  # 민들레 / 우효
        "originalKey": "D", "timeSignature": "4/4", "timeNote": "mymusic5 악보 표기",
        "bpm": 120, "shift": 4, "bpmNote": "mymusic5 120bpm",
        "stage": 3,
        "sections": [
            {"name": "Verse", "bars": [["D"], ["C#m", "F#"], ["Bm", "D"], ["Em", "A"], ["D"], ["C#m", "F#"], ["Bm", "Am", "D"], ["Em", "A"]]},
            {"name": "Chorus", "bars": [["Em", "A"], ["F#m", "B"], ["Em"], ["A"], ["D"], ["C#m", "F#"], ["Bm"], ["Am", "D"]]},
            {"name": "Outro", "bars": [["G"], ["D"], ["Em"], ["A"], ["D"]]},
        ],
        "stroke": "↓ ↓↑ ↑↓↑ (칼립소 리듬, 120bpm)",
        "percussive": "2·4박에 엄지 옆면으로 브릿지 근처를 쳐서 '쿵-척' 느낌을 만든다.",
        "why": "코드 수가 많아 3단계 곡. 원터치로 멜로디만 따라간 뒤 정식 코드로 넓힌다.",
        "evidence": [
            ("악보바다 원키 D", "http://www.akbobada.com/musicDetail.html?musicID=90222", "원키 D(라장조)"),
            ("mymusic5 4/4 120bpm", "https://www.mymusic5.com/ko/thehomeguitar/376631", "박자 4/4 · 템포 120bpm · 카포 2"),
            ("코드악보 PDF(2capo C)", "https://patross0303.com/wp-content/uploads/2023/08/%EC%9A%B0%ED%9A%A8-%EB%AF%BC%EB%93%A4%EB%A0%88-%EC%BD%94%EB%93%9C%EC%95%85%EB%B3%B4.pdf", "2Capo C Key(원키 D), 마디별 코드"),
        ],
    },
    "verified-003": {
        "percussiveReady": True,  # Thank You / Dido
        "originalKey": "B", "timeSignature": "4/4", "timeNote": "chordharbor·hooktheory 표기",
        "bpm": 79, "shift": 4, "bpmNote": "hooktheory 79bpm",
        "stage": 1,
        "sections": [
            {"name": "Intro", "bars": [["G#m"], ["G#m"]]},
            {"name": "Verse", "bars": [["G#m", "F#"], ["G#m", "F#"], ["G#m", "F#"], ["G#m", "G#m"]]},
            {"name": "Chorus", "bars": [["B", "E"], ["B", "E"], ["B", "E"], ["D#m", "C#m"]]},
        ],
        "stroke": "↓ · ↓ ↑ · ↑ ↓ ↑ (8분 스트럼, 마디마다 코드 1개)",
        "percussive": "Verse는 손바닥 뮤트로 조용히, Chorus 진입에 맞춰 2·4박 바디 톡.",
        "why": "모든 코드가 한 마디씩, 4/4 8비트라 오른손을 처음 익히기에 가장 좋다.",
        "evidence": [
            ("chordharbor 키·코드·BPM", "https://chordharbor.com/songs/thank-you/", "B major(G shapes capo4) · 4/4 · ≈80bpm · Verse/Chorus 마디별 코드"),
            ("Hooktheory", "https://www.hooktheory.com/theorytab/view/dido/thank-you", "Key G#m/B, Tempo 79, Meter 4/4"),
        ],
    },
    "verified-004": {  # Ten Thousand Hours
        "originalKey": "Ebm", "timeSignature": "4/4", "bpm": 83,
        "timeNote": "SongBPM 기준 4/4",
        "bpmNote": "SongBPM 83 (사이트별 80~85 차이)",
        "stage": 1,
        "partial": ("원곡 가수·키(E♭m 참고)·83bpm·4/4·코드 후보(B→G♭→B♭m→E♭m)만 확인한 부분 확인 상태입니다. "
                    "힙합 트랙이라 기타 반주 정식 악보가 없고, 코드는 온라인 코드표 후보를 4박 카드로 정리한 연습용입니다. "
                    "BPM은 사이트별 80~85로 차이가 있어 원음에 맞춰 확인이 필요하고, 악보 원문은 복제하지 않고 열람 링크만 연결합니다."),
        "sections": [
            {"name": "A (E♭m키 · 코드 후보)", "bars": [["B"], ["Gb"], ["Bbm"], ["Ebm"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (83bpm, 마디마다 코드 하나)",
        "why": "B → G♭ → B♭m → E♭m 네 코드 순환. B·B♭m은 원터치 10버튼에 없어 SimplifyChord 슬롯으로 넘기고, G♭·E♭m은 카포로 버튼에 맞춘다.",
        "evidence": [
            ("코드표(Gotabs)", "https://www.gotabs.com/macklemore/ten-thousand-hours-chords",
             "B → G♭ → B♭m → E♭m 코드 후보 · 원문 복제 없이 열람 링크만"),
            ("코드·템포(Chordu)", "https://chordu.com/chords-tabs-macklemore-ryan-lewis-ten-thousand-hours-lyrics-hq-id_hClRPa0jfyA",
             "코드 후보 참고"),
            ("BPM·박자(SongBPM)", "https://songbpm.com/%40macklemore-ryan-lewis/ten-thousand-hours",
             "83 BPM · 4/4 (사이트별 80~85)"),
        ],
    },
    "verified-005": {  # 추억이면 / 부활
        "originalKey": "", "missing": "부활 '추억이면' 코드표 미확보",
    },
    "verified-006": {  # 희재 / 성시경
        "originalKey": "E", "timeSignature": "4/4", "timeNote": "코드표 4코드/줄 기준(일부 편곡 악보는 6/8 표기)",
        "bpm": 64, "shift": 2, "bpmNote": "발라드 템포 추정(악보별 6/8·♩.=40 표기 존재)",
        "stage": 3,
        "sections": [
            {"name": "Verse", "bars": [["E", "B"], ["C#m", "A"], ["F#m", "B"], ["F#m7", "B"]]},
            {"name": "Pre", "bars": [["C#m", "A"], ["B", "E"], ["D", "A"], ["E", "B"]]},
            {"name": "Chorus", "bars": [["E", "A"], ["D#m7", "G#7"], ["C#m", "E"], ["A", "B"]]},
            {"name": "Outro", "bars": [["C#m", "A"], ["B", "E"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (느린 8분, 코드는 마디 앞에서 미리)",
        "percussive": "1단계에서는 쓰지 않는다. 후렴 마지막 두 마디만 4박에 약하게 바디.",
        "why": "성시경 원키 E는 남성에게도 높다. 2키 내린 D로 부르고, C#m7·F#7은 SimplifyChord 슬롯으로 넘긴다.",
        "evidence": [
            ("chordtool 원키 E·남자키 D", "https://chordtool.com/%EC%84%B1%EC%8B%9C%EA%B2%BD/%ED%9D%AC%EC%9E%AC", "원키 E / 남자키 D / 여자키 G"),
            ("코드악보(D키)", "https://guitarakbo.tistory.com/329", "D A Bm G Em A Em7 C#m7 F#7 진행"),
            ("악보 메타(6/8·♩.=40)", "https://www.mymusic5.com/ko/ori/380450", "박자 6/8(변박 3회) · 템포 ♩.=40"),
        ],
    },
    "verified-007": {  # 한숨 / 이하이
        "originalKey": "Ab", "timeSignature": "4/4", "timeNote": "kokomu 악보 표기",
        "bpm": 62, "shift": 5, "bpmNote": "ezcho 62bpm · 슬로우 고고",
        "stage": 1,
        "sections": [
            {"name": "Intro", "bars": [["Ab", "Cm7"], ["Bbm7", "Eb7"]]},
            {"name": "Verse", "bars": [["Ab", "Cm7"], ["Bbm7", "Eb7"], ["Ab"], ["Db", "Eb7"], ["Cm7", "Fm7"], ["Bbm7", "Eb7"]]},
            {"name": "Chorus", "bars": [["Db", "Eb7"], ["Cm7", "Fm7"], ["Bbm7", "Eb"], ["Ab"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (슬로우 고고, 62bpm)",
        "percussive": "후렴에서 3·4박을 손바닥으로 막았다 놓는 '컷'만 넣어도 훨씬 살아난다.",
        "why": "G·Bm7·Am7·D7 네 코드가 계속 도는 곡. 원터치 버튼 4개로 끝까지 갈 수 있다.",
        "evidence": [
            ("쉬운코드 ezcho", "http://www.ezcho.com/chop/4340", "원키 Ab · 카포1(G 운지) · bpm 62 · 코드 C Bm Am G D"),
            ("kokomu 악보(원키 Ab)", "https://www.kokomu.jp/sheet-music/han-ssum-lee-hi-144007", "조성 ♭4개(Ab) · 4/4"),
            ("코드악보", "https://guitarakbo.tistory.com/241", "CM7 Bm7 Am7 D7 GM7 진행"),
        ],
    },
    "verified-008": {  # 내가 너의 곁에 잠시 살았다는 걸 / 토이
        "originalKey": "C", "timeSignature": "4/4", "timeNote": "doyac 악보 4/4",
        "bpm": 65, "shift": 0, "bpmNote": "songbpm 129 → 2배수 표기, 실질 65bpm",
        "stage": 3,
        "sections": [
            {"name": "Intro", "bars": [["C", "Dm7"], ["Em7", "Am7"], ["F", "G"]]},
            {"name": "Verse", "bars": [["C", "Dm7"], ["Em7", "Am7"], ["F", "G/F"], ["Em7", "Am7"]]},
            {"name": "Chorus", "bars": [["F", "G"], ["Em7", "Am7"], ["Dm7", "G"], ["C"]]},
        ],
        "stroke": "↓ · ↓↑ · ↑↓ (8분 아르페지오 섞은 발라드 스트럼)",
        "percussive": "3단계 이후 곡. 브릿지에서 4박만 컷.",
        "why": "Dm7·Em7·Am7 같은 7th 코드가 많아 3단계. 원곡 C키가 남성에게 무리 없어 그대로 쓴다.",
        "evidence": [
            ("악보교실 원키 C", "https://www.akboclass.co.kr/item/17004", "멜로디+코드+가사 C 원키"),
            ("songbpm", "https://songbpm.com/@toy/naega-neoyi-gyeote-jamsi-salassdaneun-geol-e5FzvBRVGA", "129 BPM(2배수) · Key C"),
            ("doyac 악보(4/4·코드)", "https://www.doyac.com/upFolder/doyacweb/upFolder/akbo_mr/sample_akbo/SAM1418032271.pdf", "4/4 · C Dm7 Em7 Am7 F G"),
        ],
    },
    "verified-009": {  # 예뻤어 / DAY6
        "originalKey": "Eb", "timeSignature": "4/4", "timeNote": "kokomu 악보 표기",
        "bpm": 84, "shift": 3, "bpmNote": "kokomu 84bpm",
        "partial": "코드표는 확보했지만 마디 배치 신뢰도가 낮아 코드 악보는 검수 대기로 둔다(키·박자·BPM만 확정).",
        "evidence": [
            ("코드악보 PDF(원키 Eb, 1capo D)", "https://patross0303.com/wp-content/uploads/2023/07/DAY6-%EC%98%88%EB%BB%A4%EC%96%B4-%EC%BD%94%EB%93%9C%EC%95%85%EB%B3%B4.pdf", "원키 Eb / 1Capo D Key"),
            ("kokomu 악보", "https://www.kokomu.jp/sheet-music/you-were-beautiful-day6-143113", "4/4 · 84bpm · 82마디"),
        ],
    },
    "verified-010": {
        "percussiveReady": True,  # 도망가자 / 선우정아
        "originalKey": "G", "timeSignature": "4/4", "timeNote": "mymusic5 악보 표기",
        "bpm": 65, "shift": 4, "bpmNote": "ChordU 64.8 · mymusic5 65bpm",
        "stage": 2,
        "sections": [
            {"name": "Intro", "bars": [["G"], ["C"], ["G"], ["Am"], ["D"]]},
            {"name": "Verse", "bars": [["G"], ["C"], ["G"], ["Am"], ["D"]]},
            {"name": "Pre", "bars": [["C", "D"], ["G"], ["Em"], ["C", "D"]]},
            {"name": "Chorus", "bars": [["G", "D"], ["C", "G"], ["A", "Cm"], ["D"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (슬로우 고고, 65bpm)",
        "percussive": "2·4박 백비트에 맞춰 오른손 손목으로 바디를 톡톡. 후렴만 넣어도 충분하다.",
        "why": "G·C·Am·D·Em 다섯 코드로 90%가 해결된다. 원터치 4버튼+슬롯 1개.",
        "evidence": [
            ("쉬운코드 ezcho", "http://www.ezcho.com/chop/4047", "원키 G · 카포 없음 · 슬로우 고고"),
            ("ChordU", "https://chordu.com/chords-tabs-%EC%84%A0%EC%9A%B0%EC%A0%95%EC%95%84-%EB%8F%84%EB%A7%9D%EA%B0%80%EC%9E%90-%EC%9C%A0%ED%9D%AC%EC%97%B4%EC%9D%98-%EC%8A%A4%EC%BC%80%EC%B9%98%EB%B6%81-20191213-id_qrjk4lfdh7Q", "Tempo 64.8bpm · G D C A Bm"),
            ("mymusic5 악보", "https://www.mymusic5.com/ko/namoobro/28273", "4/4 · 65bpm · 조성 ♯1개"),
        ],
    },
    "verified-011": {  # 청혼 / 노을
        "originalKey": "E", "timeSignature": "4/4", "timeNote": "발라드 4/4(악보 표기 확인 필요)",
        "bpm": 0, "shift": 3,
        "partial": "원키 E만 확인. 노을 버전 코드표를 확보하지 못해 코드 악보는 검수 대기.",
        "evidence": [
            ("악보바다 원키 E", "https://www.akbobada.com/musicDetail.html?musicID=48233", "원키 E(마장조)"),
        ],
    },
    "verified-012": {
        "percussiveReady": True,  # TOMBOY / 혁오
        "originalKey": "Eb", "timeSignature": "4/4", "timeNote": "idamscore·mymusic5 표기",
        "bpm": 74, "shift": 0, "bpmNote": "mymusic5 74bpm",
        "stage": 2,
        "sections": [
            {"name": "Verse", "bars": [["Eb"], ["Cm"], ["Fm", "G"], ["Cm", "Bb"]]},
            {"name": "Verse 2", "bars": [["Ab", "Bb"], ["Eb"], ["Ab", "Bb"], ["Eb"]]},
            {"name": "Chorus", "bars": [["Eb", "Bb"], ["Cm", "G"], ["Ab", "Bb"], ["Eb"]]},
            {"name": "Bridge", "bars": [["Cm"], ["Ab"], ["Fm"], ["Eb"]]},
        ],
        "stroke": "↓ ↓↑ ↑ ↓↑ (한 마디에 두 코드, 4·2박 교대)",
        "percussive": "브릿지 이후 4박에 'X' 척킹을 넣으면 원곡 드럼의 킥 느낌이 난다.",
        "why": "Eb키지만 카포 3 + C 모양으로 누르면 원터치 버튼 그대로. Cm만 슬롯 1번.",
        "evidence": [
            ("악보바다 원키 Eb", "https://www.akbobada.com/musicDetail.html?musicID=71135", "원키 Eb(내림 마장조)"),
            ("코드악보(3capo C)", "https://guitarakbo.tistory.com/79", "C Am Dm E Am D F G 진행"),
            ("mymusic5 4/4 74bpm", "https://www.mymusic5.com/ko/tunacracker/517750", "E♭장조 · 4/4 · 74bpm"),
            ("idamscore 4/4", "https://idamscore.com/40/?idx=468", "Key Eb Major · 4/4"),
        ],
    },
    "verified-013": {
        "percussiveReady": True,  # Flower / 오반
        "originalKey": "A", "timeSignature": "4/4", "timeNote": "mymusic5·Chordify 표기",
        "bpm": 88, "shift": 2, "bpmNote": "Chordify 88bpm",
        "stage": 1,
        "sections": [
            {"name": "Intro", "bars": [["A"], ["F#m"], ["D"], ["E"]]},
            {"name": "Verse", "bars": [["A"], ["F#m"], ["D"], ["E"]]},
            {"name": "Chorus", "bars": [["A"], ["E"], ["F#m"], ["D"]]},
        ],
        "stroke": "↓ ↓↑ ↑↓↑ (4/4 8비트, 한 마디 한 코드)",
        "percussive": "후렴 2·4박에 바디 톡 + 4박 뒤 'X'. 결혼식 축가라 과하지 않게.",
        "why": "I–vi–IV–V 네 코드뿐. 오른손 8비트를 익히는 첫 곡으로 좋다.",
        "evidence": [
            ("Chordify 키·BPM", "https://chordify.net/chords/oban-i-bon-in-gyeolhonsig-eseo-anaeege-bulleojun-chugga-oban-ovan-flower-3-13-balmae-romanticfactory", "Key A major · BPM 88 · F#m E A D"),
            ("악보바다 원키 A", "https://www.akbobada.com/musicDetail.html?musicID=95147&partTabGubun=B", "원키 A(가장조)"),
            ("mymusic5 4/4 88bpm", "https://www.mymusic5.com/video/288887", "A major · 4/4 · 88bpm · 61마디"),
        ],
    },
    "verified-014": {  # 死別 / Shannon
        "originalKey": "", "missing": "보컬 중심 곡, 코드표 미확보",
    },
    "verified-015": {
        "percussiveReady": True,  # Englishman in New York / Sting
        "originalKey": "Bm", "timeSignature": "4/4", "timeNote": "hooktheory·songparts 표기",
        "bpm": 102, "shift": 2, "bpmNote": "hooktheory 102bpm",
        "stage": 2,
        "sections": [
            {"name": "Intro", "bars": [["Em7"], ["A7"], ["Bm"], ["Bm"]]},
            {"name": "Verse", "bars": [["Em7", "A7"], ["Bm"], ["Em7", "A7"], ["Bm"]]},
            {"name": "Chorus", "bars": [["Em", "A"], ["Bm"], ["Em", "A"], ["Bm"]]},
            {"name": "Bridge", "bars": [["D"], ["A7"], ["Bm"], ["G", "A"]]},
        ],
        "stroke": "↓ X ↑ X ↓ X ↑ X (레게/스카 느낌의 8분 업스트로크)",
        "percussive": "2·4박을 손바닥으로 완전히 막는 '스카 척'이 이 곡의 핵심 리듬이다.",
        "why": "Bm(바레)이 계속 나오지만 4개 코드로 반복된다. 손날 뮤트로 리듬을 먼저 익히면 재밌다.",
        "evidence": [
            ("Hooktheory", "https://www.hooktheory.com/theorytab/view/sting/englishman-in-new-york", "Key Bm · Tempo 102 · Meter 4/4"),
            ("lamucal 코드표", "https://lamucal.com/chords/sting/englishman-in-new-york-195869", "Em7 A7 Bm / Chorus Em A Bm"),
            ("songparts", "https://songparts.com/songs/sting/englishman-in-new-york", "B minor · 102 BPM · 4/4"),
        ],
    },
    "verified-016": {  # How To Cry / Sam Smith
        "originalKey": "E", "timeSignature": "4/4", "timeNote": "musicnotes·SongBPM 표기",
        "bpm": 90, "shift": 2, "bpmNote": "SongBPM 90bpm",
        "stage": 2,
        "sections": [
            {"name": "Verse", "bars": [["E"], ["F#m7"], ["C#m7"], ["B"]]},
            {"name": "Pre", "bars": [["E"], ["F#m7"], ["C#m7"], ["B"]]},
            {"name": "Chorus", "bars": [["A", "E"], ["C#m7", "B"], ["A", "E"], ["C#m7", "B"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (한 마디 한 코드, 느린 8비트)",
        "percussive": "후렴 'taught you how to cry' 자리에서 4박 뒤 바디 한 번.",
        "why": "4개 코드가 반복되고 느려서 영어 버스킹 첫 곡으로 좋다.",
        "evidence": [
            ("publictabs 코드표", "https://publictabs.com/song?s=sam-smith-how-to-cry", "Key D(capo2 E) · 93 BPM · 4/4 · D Em7 Bm7 A G"),
            ("musicnotes", "https://www.musicnotes.com/sheetmusic/sam-smith/how-to-cry/MN0269418", "E Major · 4/4 · ♩=92"),
            ("SongBPM", "https://songbpm.com/@sam-smith/how-to-cry-wlaqs", "90 BPM · 4 beats per bar"),
        ],
    },
    "verified-017": {  # 나는 버려질 장난감
        "originalKey": "", "missing": "자동분석 코드 후보만 있고 청음 검수 전",
    },
    "verified-018": {
        "percussiveReady": True,  # たぶん / YOASOBI
        "originalKey": "F", "timeSignature": "4/4", "timeNote": "ChordWiki 표기",
        "bpm": 90, "shift": 4, "bpmNote": "ChordWiki BPM 90",
        "stage": 3,
        "sections": [
            {"name": "Intro", "bars": [["BbM7", "C"], ["Am7", "Dm"]]},
            {"name": "Verse", "bars": [["BbM7", "C"], ["Am7", "Dm"], ["BbM7", "A7"], ["Dm"]]},
            {"name": "Chorus", "bars": [["BbM7", "C"], ["Am7", "Dm"], ["Gm7", "A7"], ["Dm"]]},
        ],
        "stroke": "↓ · ↓↑ ↑ · ↓↑ (하프타임 셔플, '타카타카' 느낌)",
        "percussive": "박자 사이에 빈 곳이 많아 오히려 척킹 연습에 좋다. 2·4박 X.",
        "why": "M7·7th 코드가 많아 3단계. 원터치로는 6번 코드까지 슬롯에 넣어야 한다.",
        "evidence": [
            ("ChordWiki", "https://ja.chordwiki.org/wiki/%E3%81%9F%E3%81%B6%E3%82%93+%28YOASOBI%29", "BPM=90 · 4/4 · Key F · 코드 BbM7 C Am7 Dm7 Gm7 A7"),
            ("楽譜PAG(원키 F, Capo1 Play E)", "https://www.at-elise.com/elise/JPDPGP02499/", "オリジナルキーF · Capo1f · Play E"),
        ],
    },
    "verified-019": {  # 생각을 멈추다 보면 / 최유리
        "originalKey": "", "missing": "코드표 미확보",
    },
    "verified-020": {  # 오르막길 / 윤종신
        "originalKey": "A", "timeSignature": "4/4", "timeNote": "mymusic5 악보 표기(변박 2회)",
        "bpm": 68, "shift": 2, "bpmNote": "mymusic5 68bpm",
        "stage": 2,
        "sections": [
            {"name": "Verse", "bars": [["A", "E"], ["F#m", "D"], ["A", "E"], ["F#m", "D"]]},
            {"name": "Chorus", "bars": [["A", "E"], ["F#m", "D"], ["B", "E"], ["A"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (한 마디 두 코드, 2박씩)",
        "percussive": "후렴에서 4박에 컷, 마지막 마디는 2·4박 톡.",
        "why": "A·E·F#m·D 네 코드가 반복된다. 원곡은 반음 전조가 있으니 마지막 후렴은 카포를 한 칸 옮겨도 좋다.",
        "evidence": [
            ("chordscore 원키 A", "https://chordscore.com/artist/%EC%9C%A4%EC%A2%85%EC%8B%A0", "오르막길 Original key A"),
            ("mymusic5 악보", "https://www.mymusic5.com/ko/ori/324151", "4/4(변박 2회) · 68bpm · 반음 전조"),
            ("ChordU", "https://chordu.com/chords-tabs-%EC%9C%A4%EC%A2%85%EC%8B%A0-%EC%98%A4%EB%A5%B4%EB%A7%89%EA%B8%B8-%EA%B0%80%EC%82%AC-yoon-jong-shin-uphill-lyrics-id_OzCaD88h8tk", "A Major · A E F#m D B"),
        ],
    },
    "verified-021": {  # 날씨가 좋고 바람도 좋아
        "originalKey": "", "missing": "가수 미확인 · 코드/키 자료 없음",
    },
    "verified-022": {  # 세상이 그대를 속일지라도 / 김장훈
        "originalKey": "C#", "timeSignature": "4/4", "timeNote": "코드표 4코드/줄 기준",
        "bpm": 70, "shift": 2, "bpmNote": "Chordify(성시경 커버) 70bpm",
        "stage": 3,
        "sections": [
            {"name": "Intro", "bars": [["C#"], ["F#"], ["C#"], ["D#m", "G#"]]},
            {"name": "Verse", "bars": [["C#", "G#/C"], ["A#m", "Fm"], ["A#7"], ["D#m", "Fm"], ["A#"], ["D#m7", "G#7"]]},
            {"name": "Chorus", "bars": [["C#", "F#"], ["G#", "Fm"], ["A#m7", "D#m7"], ["G#7", "C#"]]},
            {"name": "Bridge", "bars": [["C#", "G#/C"], ["A#m", "F#m"], ["C#", "A#m"], ["D#m7", "G#"], ["C#"]]},
        ],
        "stroke": "↓ · ↓↑ · ↑↓↑ (느린 8분, 후렴에서 세게)",
        "percussive": "브릿지 '세상이 그대를…'에서 1박만 세게 치고 나머지 컷. 감정이 실린다.",
        "why": "원키 C#(올림다장르). 코드표는 C로 적혀 있어 카포 1로 올리면 원키가 된다. 남성 고음이라 2키 내리는 걸 권한다.",
        "evidence": [
            ("나무위키 조성 C#", "https://namu.wiki/w/%EC%84%B8%EC%83%81%EC%9D%B4%20%EA%B7%B8%EB%8C%80%EB%A5%BC%20%EC%86%8D%EC%9D%BC%EC%A7%80%EB%9D%BC%EB%8F%84", "조성 올림다장조(C#) · 최고음 A#4"),
            ("코드악보(C키)", "https://tartae.tistory.com/entry/%EA%B9%80%EC%9E%A5%ED%9B%88-%EC%84%B8%EC%83%81%EC%9D%B4-%EA%B7%B8%EB%8C%80%EB%A5%BC-%EC%86%8D%EC%9D%BC%EC%A7%80%EB%9D%BC%EB%8F%84-%EC%BD%94%EB%93%9C%EC%95%85%EB%B3%B4", "C F Dm G Am Em A7 진행"),
            ("Chordify(성시경)", "https://chordify.net/chords/gimjanghunxseongsigyeong-sesang-i-geudaeleul-sog-iljilado-deo-sijeunjeu-seongsigyeong-ui-gomagnamchin-kbs-260814-bangsong-kbs-k", "Key Db major · BPM 70"),
        ],
    },
    "verified-023": {  # 사랑한 마음엔 죄가 없다 / 소란
        "originalKey": "Gb", "timeSignature": "4/4", "timeNote": "발라드 4/4",
        "bpm": 0, "shift": 3,
        "partial": "원키 Gb만 확인. 코드표·BPM 미확보로 코드 악보는 검수 대기.",
        "evidence": [
            ("악보바다 원키 Gb", "https://www.akbobada.com/musicDetail.html?musicID=97191", "원키 Gb(내림 사장조)"),
        ],
    },
    "verified-024": {  # 닮은 사람 / 이기찬 — MR 화면 녹화 오디오 실측(2026-11-22)
        "originalKey": "D", "timeSignature": "4/4",
        "timeNote": "MR 오디오 실측 — 0.619초부터 3.75초 마디(킥 1·3박, 스네어 2·4박)",
        "capo": 2,  # C폼+2 = D. 원터치 버튼 C·Dm·Em·F·G·Gm로 D·Em·F#m·G·A·Am이 그대로 잡힌다
        "bpm": 64, "bpmNote": "오디오 실측 ♩≈64(박 0.9375초) · 하이햇 8분 · 128 더블 표기 아님",
        "stage": 3,
        "percussiveReady": True,
        "partial": ("MR 오디오 분석 기반 — 주성 님이 올린 TJ노래방 ‘멜로디제거’ MR 화면 녹화(3분 37초)에서 직접 뽑은 값입니다. "
                    "4/4, BPM 64, 원키 D는 화면의 ‘현재음정 남성 D’ 표기와 오디오 실측(킥은 1박과 3박, 스네어는 2박과 4박, 한 마디 3.75초)이 일치합니다. "
                    "코드는 8분 격자 크로마와 저역 근음, 박별 스펙트럼 피크를 함께 보고 옮긴 초안이라, 마디 안 패스 코드와 7th/sus 유무는 청음 확인이 필요합니다. "
                    "이기찬 2025 리메이크(작사 조은희, 작곡 조우진)는 테이 2004 원곡의 리메이크이고, TJ 화면에도 원곡이 tei로 표기됩니다(테이 원곡 악보 키는 E♭). "
                    "마지막 후렴(2:45~)은 반음 올라가 E♭로 조바꿈하므로, 악보는 같은 코드 모양으로 칠 수 있게 D 기준으로 옮겨 적었습니다 — 원키로 부르려면 Capo를 한 칸 더 올리세요. "
                    "악보 원문은 복제하지 않고 열람 링크만 연결합니다."),
        "basis": ("MR 오디오 3분 37초에서 3.75초 마디 격자로 마디별 코드를 뽑아 4박 카드로 옮긴 초안입니다. "
                  "화면 표기 남성 D와 실측 D키, 킥 1박·3박, 스네어 2박·4박이 일치합니다. 마디 안 패스 코드와 7th/sus 유무는 청음으로 확인해 주세요."),
        "sections": [
            {"name": "전주 · 0:00", "bars": [["D"], ["Bm", "B7"], ["Em", "D"]]},
            {"name": "1절 · 0:12", "bars": [["C"], ["A"], ["D", "F#m"], ["G", "F#m"],
                                            ["Em", "A7"], ["Am", "B7"], ["Em", "D/F#"], ["G", "D/F#"]]},
            {"name": "1절 후반 · 0:42", "bars": [["Em", "G"], ["A"], ["F#m", "G"], ["A", "D"],
                                               ["G", "Em7"], ["G", "A"], ["A"]]},
            {"name": "후렴 · 1:08", "bars": [["A", "D/F#"], ["Bm", "B7"], ["B7", "Em7"], ["A", "Am"],
                                           ["B7", "Em7"], ["F#m", "G"], ["G", "Em7"], ["A7"]]},
            {"name": "2절 · 1:38", "bars": [["Bm", "D"], ["G", "A"], ["Bm", "C#m"], ["D", "G"]]},
            {"name": "후렴 2 · 1:53", "bars": [["Em7", "C"], ["A"], ["D"], ["Bm", "B7"],
                                             ["Em7", "A"], ["C", "B7"], ["Em7", "D"], ["G"]]},
            {"name": "브릿지 · 2:23", "bars": [["Em", "A"], ["G", "A"], ["Bb", "A"], ["Gm", "F#m"],
                                           ["Em"], ["A"]]},
            {"name": "마지막 후렴 · 2:45 (원곡 E♭→D)", "bars": [["D", "A"], ["D"], ["Bm"], ["Em", "A"],
                                                          ["F#m", "Bm"], ["Em", "F#m"], ["G", "D"],
                                                          ["Em", "F#m"], ["Bm", "A"]]},
            {"name": "아웃트로 · 3:19 (원곡 E♭→D)", "bars": [["A", "G"], ["D", "A"], ["A", "D"], ["D"], ["D", "A"]]},
        ],
        "stroke": "♩=64 · 한 마디 4박에 코드 2개(2박씩) — ↓ · ↓↑ 로 시작해 후렴은 8분으로 채운다",
        "percussive": "후렴 2·4박에 오른손 손날로 바디를 톡(X). 브릿지 ‘다시 길들여지는 게’는 1박만 세게 치고 나머지는 컷.",
        "why": ("남성 원곡 D키라 원키 그대로(C폼 + 카포 2). C(♭VII)·B7·Am·B♭ 같은 색채 코드가 섞여 3단계 곡. "
                "원터치 버튼으로 후렴(A·D·Em·G·F#m·Am)만 먼저 잡고, 슬롯에 Bm·B7·C를 넣어 1절로 넓힌다. "
                "한 마디에 코드가 두 번 바뀌므로 64bpm에서 2박 단위로 손을 미리 옮기는 연습이 핵심."),
        "evidence": [
            ("TJ노래방 수록 정보(닮은사람 · 이기찬)", "https://noraebang.app/songs/tj/87362",
             "TJ 87362 · 작곡 조우진 · 작사 조은희 — 분석한 MR 영상과 같은 반주"),
            ("악보바다 테이 원곡 악보 메타", "https://www.akbobada.com/musicDetail.html?musicID=12225",
             "테이 2004 원곡 · 원키 E♭(내림 마장조) · MR/멜로디 악보 수록"),
            ("ChordTool 이기찬 곡 정보", "https://chordtool.com/%EC%9D%B4%EA%B8%B0%EC%B0%AC/%EB%8B%AE%EC%9D%80-%EC%82%AC%EB%9E%8C",
             "이기찬 2025.06 발매 · 작곡 조우진 · 작사 조은희(테이 원곡과 같은 작가) · 코드악보 미등록"),
            ("벅스 이기찬 ‘닮은 사람’ 곡 정보", "https://music.bugs.co.kr/track/6298142",
             "재생 시간 03:40 · 보컬 이기찬 · 편곡 승찬"),
        ],
    },
    "verified-025": {  # 히로인 / back number
        "originalKey": "G", "timeSignature": "4/4", "timeNote": "ChordWiki 4/4",
        "bpm": 77, "shift": 2, "bpmNote": "ChordWiki BPM 77",
        "stage": 3,
        "sections": [
            {"name": "Intro", "bars": [["G", "D/F#"], ["F", "E"], ["Am", "Bm"], ["Cm", "D"]]},
            {"name": "Verse", "bars": [["G", "Bm"], ["C", "G"], ["D/F#"], ["Em", "Bm"], ["C", "D"]]},
            {"name": "Pre", "bars": [["C", "D"], ["Em", "G7"]]},
            {"name": "Chorus", "bars": [["D", "G"], ["Em"], ["C", "D"], ["G", "Em"], ["C", "D"], ["G"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (4/4 8분, 일본어 가사는 한 소절씩 끊어서)",
        "percussive": "후렴 끝 '모오 오보에테이루' 자리에서 2·4박 바디.",
        "why": "D/F#·Bm·Cm 같은 전위/마이너 코드가 나와 3단계. 원터치로는 5개, 나머지는 슬롯.",
        "evidence": [
            ("ChordWiki", "https://ja.chordwiki.org/wiki/%E3%83%92%E3%83%AD%E3%82%A4%E3%83%B3+%28back+number%29", "BPM=77 · 4/4拍子 · 마디별 코드"),
            ("music-chord 코드표", "https://music-chord.com/songs/%E3%83%92%E3%83%AD%E3%82%A4%E3%83%B3-back%20number/", "BPM 76 · 카포 없음 · Key G"),
        ],
    },

    # ── 복원·확인 19곡 ───────────────────────────────────────────
    "restored-096": {
        "percussiveReady": True,  # And July / 헤이즈
        "originalKey": "Dm", "timeSignature": "4/4", "timeNote": "Chordify 표기",
        "bpm": 100, "shift": 0, "bpmNote": "Chordify 100bpm",
        "stage": 3,
        "sections": [
            {"name": "Intro", "bars": [["BbM7", "A7"], ["Dm", "G7"]]},
            {"name": "Verse", "bars": [["BbM7", "A7"], ["Dm", "G7"], ["BbM7", "A7"], ["Dm"]]},
            {"name": "Chorus", "bars": [["F", "Bb"], ["Eb", "G7"]]},
        ],
        "stroke": "↓ X ↑ X ↓ X ↑ X (힙합 비트, 4분 다운+8분 업)",
        "percussive": "2·4박 척킹이 곡의 전부. 손바닥을 줄에 얹었다 떼며 '칩' 소리를 낸다.",
        "why": "BbM7–A7–Dm–G7 네 코드가 계속 도는 힙합 트랙. 퍼커시브 리듬 연습에 딱 좋다.",
        "evidence": [
            ("Chordify", "https://chordify.net/chords/heize-feat-dean-dj-friz-songs/and-july-chords", "Key D minor · BPM 100 · Bb A Dm Gm"),
            ("악보바다 원키 Dm", "https://www.akbobada.com/musicDetail.html?musicID=69202", "원키 Dm(라단조)"),
            ("코드악보", "https://tartae.tistory.com/entry/%ED%97%A4%EC%9D%B4%EC%A6%88-And-July-%EC%BD%94%EB%93%9C%EC%95%85%EB%B3%B4", "BbM7 A7 Dm9 G7 반복"),
        ],
    },
    "restored-119": {  # 비도 오고 그래서 / 헤이즈
        "originalKey": "C#m", "timeSignature": "4/4", "timeNote": "mymusic5·idamscore 표기",
        "bpm": 79, "shift": 4, "bpmNote": "Chordify 79bpm",
        "stage": 3,
        "sections": [
            {"name": "Intro", "bars": [["C#m", "G#m"], ["A", "E"]]},
            {"name": "Verse", "bars": [["C#m", "G#m"], ["A", "E"], ["F#m", "G#m"], ["A", "B"]]},
            {"name": "Chorus", "bars": [["C#m", "G#m"], ["A", "E"], ["F#m", "B"], ["E"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (느린 8분, 코드는 2박마다)",
        "percussive": "후렴 2·4박에 손날 톡. 비 오는 날 감성에 맞춰 작게.",
        "why": "C#m·G#m(A♭m)·A·E로 단조 진행이 반복. 원터치는 4키 내린 A단조로 잡으면 대부분 버튼에 들어온다.",
        "evidence": [
            ("chordtool 원키 C#m·남자키 Gm", "https://chordtool.com/%ED%97%A4%EC%9D%B4%EC%A6%88/%EB%B9%84%EB%8F%84-%EC%98%A4%EA%B3%A0-%EA%B7%B8%EB%9E%98%EC%84%9C-%28Feat.%EC%8B%A0%EC%9A%A9%EC%9E%AC%29", "원키 C#m · 남자키 Gm · 코드 C#m7 G#m Amaj7 Emaj7 F#m7"),
            ("idamscore 4/4", "https://idamscore.com/shop_view/206", "Key d minor(원곡 c#) · 4/4"),
            ("Chordify 79bpm", "https://chordify.net/chords/heize-feat-sin-yongjae-songs/bido-ogo-geulaeseo-chords", "Key E major · BPM 79"),
        ],
    },
    "restored-122": {  # Vancouver / BIG Naughty
        "originalKey": "F#", "timeSignature": "4/4", "timeNote": "mymusic5 악보 표기",
        "bpm": 89, "shift": 3,
        "partial": "키·박자·BPM만 확인. 코드표(전조 표기)가 자동 변환표라 마디 배치를 확정하지 못해 검수 대기.",
        "evidence": [
            ("mymusic5 악보", "https://www.mymusic5.com/video/68728", "Key 5 flats · 4/4 · 90bpm · Capo 1"),
            ("12notez", "https://12notez.in/song/vancouver-big-naughty", "Key F# Major · 89 BPM"),
        ],
    },
    "restored-123": {  # 안아줘 / 정준일
        "originalKey": "C", "timeSignature": "4/4", "timeNote": "ezcho 슬로우 고고 표기",
        "bpm": 68, "shift": 0, "bpmNote": "ezcho 68bpm",
        "stage": 2,
        "sections": [
            {"name": "Intro", "bars": [["F", "Fm"], ["C"]]},
            {"name": "Verse", "bars": [["F", "Fm"], ["C"], ["F", "Fm"], ["C"]]},
            {"name": "Chorus", "bars": [["F", "Fm"], ["Em", "Am"], ["Dm", "G"], ["C"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (느린 8분, 68bpm)",
        "percussive": "후렴 '내 곁에 있어줘'에서 4박 컷 한 번.",
        "why": "F와 Fm이 번갈아 나오는 곡. F는 바레라 SimplifyChord 1번에 넣고 약식으로 잡는다.",
        "evidence": [
            ("쉬운코드 ezcho", "http://www.ezcho.com/chop/4399", "원키 C · 카포 없음 · bpm 68 · F Fm C Am Em Dm G"),
            ("악보바다 원키 C", "https://www.akbobada.com/albumdetailedpage.html?albumID=14841", "기타 악보 C 5P"),
            ("코드악보", "https://tartae.tistory.com/entry/%EC%A0%95%EC%A4%80%EC%9D%BC-%EC%95%88%EC%95%84%EC%A4%98-%EC%BD%94%EB%93%9C%EC%95%85%EB%B3%B4", "FM7 Fm6 C9 Em7 Am7 Dm7 G7sus4"),
        ],
    },
    "restored-125": {  # 미안해 미워해 사랑해 / 크러쉬
        "originalKey": "E", "timeSignature": "4/4", "timeNote": "mymusic5·cifraclub 표기",
        "bpm": 65, "shift": 2, "bpmNote": "악보에 129bpm(2배수) 표기 → 65bpm으로 연습",
        "stage": 2,
        "sections": [
            {"name": "Intro", "bars": [["E", "C#m"], ["B", "A"]]},
            {"name": "Verse", "bars": [["E", "C#m"], ["B", "A"], ["E", "C#m"], ["B", "A", "Am"]]},
            {"name": "Chorus", "bars": [["A", "B"], ["E", "B"], ["C#m", "A"], ["B", "E"]]},
        ],
        "stroke": "↓ · ↓↑ · ↑↓↑ (느린 8분 발라드)",
        "percussive": "후렴 마지막 '유일한 이유'에서 4박에 바디, 나머지는 컷.",
        "why": "E·C#m·B·A에 Am 하나. 크러쉬 저음이라 2키 내리면 편하다.",
        "evidence": [
            ("악보바다 원키 E", "https://www.akbobada.com/musicDetail.html?musicID=91895&partTabGubun=S", "원키 E(마장조)"),
            ("mymusic5 4/4 129bpm", "https://www.mymusic5.com/ko/rita-b/190199", "E장조 · 4/4 · 129bpm · 코드 E C#m B A (Am)"),
            ("Cifra Club 코드표(Key E)", "https://www.cifraclub.com.br/crush-k-pop/love-you-with-all-my-heart-mianhae-miwohae-salanghae/", "E C#m B A Am 진행"),
        ],
    },
    "restored-130": {  # 첫눈처럼 너에게 가겠다 / 에일리
        "originalKey": "Fm", "timeSignature": "4/4", "timeNote": "guitarworld 4/4",
        "bpm": 67, "shift": 4, "bpmNote": "padomusic·guitarworld 67bpm",
        "stage": 3,
        "sections": [
            {"name": "Verse", "bars": [["Fm", "C#"], ["D#", "A#m"], ["Cm", "C#"]]},
            {"name": "Chorus", "bars": [["Fm", "C#"], ["D#", "A#m"], ["C#", "D#"], ["Fm"]]},
        ],
        "stroke": "↓ · ↓↑ · ↑↓↑ (느린 8분, 후렴은 16분으로)",
        "percussive": "후렴 2·4박에 톡, 마지막 마디는 크게 한 번.",
        "why": "Fm 단조. 4키 내리면 C#m 단조가 되어 원터치 버튼 대부분에 들어온다.",
        "evidence": [
            ("파도뮤직 원키 Fm·67", "https://www.padomusic.com/songs/2/", "원키 F minor · BPM 67 · 음역 G3~E5"),
            ("guitarworld 4/4 67bpm", "https://www.guitarworld.com.cn/pu/q86317", "原调 Fm→F#m · 4/4 · 67bpm · Capo1"),
            ("악보교실 원키 Fm", "https://www.akboclass.co.kr/item/4531", "멜로디+코드+가사 Fm 원키"),
        ],
    },
    "restored-131": {  # 0+0 / 한로로
        "originalKey": "A", "timeSignature": "4/4", "timeNote": "mymusic5 악보 표기",
        "bpm": 68, "shift": 4, "bpmNote": "mymusic5 68bpm",
        "stage": 2,
        "sections": [
            {"name": "Verse", "bars": [["A", "Amaj7"], ["F#", "Bm7"], ["E7", "D"]]},
            {"name": "Chorus", "bars": [["A", "E"], ["F#", "D"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (68bpm 8비트)",
        "percussive": "브릿지에서 4박 'X'. 일렉 기타 원곡이라 어쿠스틱은 조금 가볍게.",
        "why": "A키 4코드 반복. 여성 원곡이라 4키 내려 F키로 부르면 편하다.",
        "evidence": [
            ("chordtool 원키 A", "https://chordtool.com/%ED%95%9C%EB%A1%9C%EB%A1%9C/0-0", "원키 A · 코드 A Amaj7 F# Bm7 E7 D"),
            ("mymusic5 4/4 68bpm", "https://www.mymusic5.com/kwanujo/349106", "A major · 4/4 · 68bpm · 50마디"),
        ],
    },
    "restored-132": {
        "percussiveReady": True,  # 사랑하게 될 거야 / 한로로
        "originalKey": "G", "timeSignature": "4/4", "timeNote": "mymusic5·파도뮤직 표기",
        "bpm": 93, "shift": 4, "bpmNote": "파도뮤직 93bpm",
        "stage": 1,
        "sections": [
            {"name": "Verse", "bars": [["G"], ["B7"], ["D"], ["Em"]]},
            {"name": "Chorus", "bars": [["G"], ["D"], ["Em"], ["C"]]},
        ],
        "stroke": "↓ ↓↑ ↑ ↓↑ (8비트, 2·4박 액센트)",
        "percussive": "곡 전체가 일렉 기타 백비트라 2·4박 척킹이 그대로 어울린다.",
        "why": "G·B7·D·Em·C 다섯 코드. B7만 슬롯에 넣으면 나머지는 버튼으로 끝난다.",
        "evidence": [
            ("파도뮤직 원키·BPM", "https://www.padomusic.com/songs/23/", "원키 G Major · BPM 93"),
            ("mymusic5 4/4 93bpm", "https://www.mymusic5.com/video/322497", "G major · 4/4 · 93bpm"),
            ("chordtool 코드", "https://chordtool.com/%ED%95%9C%EB%A1%9C%EB%A1%9C/%EC%82%AC%EB%9E%91%ED%95%98%EA%B2%8C-%EB%90%A0-%EA%B1%B0%EC%95%BC", "G B7 D Em C G7"),
        ],
    },
    "restored-140": {  # 예뻤어(중복 표기)
        "originalKey": "", "missing": "verified-009와 같은 곡 · 코드 미확정",
    },
    "restored-142": {  # 청혼하지 않을 이유를 못 찾았어 / 이무진
        "originalKey": "D", "timeSignature": "4/4", "timeNote": "피아노 악보 표기",
        "bpm": 96, "shift": 2, "bpmNote": "마피아 악보 템포 96",
        "stage": 2,
        "sections": [
            {"name": "Verse", "bars": [["D", "A"], ["Bm7", "G"], ["D", "A"], ["G"]]},
            {"name": "Pre", "bars": [["Em7", "A7"], ["D", "G"]]},
            {"name": "Chorus", "bars": [["D", "A"], ["Bm7", "G"], ["D", "A"], ["G", "A"]]},
        ],
        "stroke": "↓ ↓↑ ↑ ↓↑ (한 마디 두 코드)",
        "percussive": "후렴 2·4박 톡 + 마지막 마디는 4박 척.",
        "why": "D키 I–V–vi–IV. Bm7만 슬롯, 나머지는 원터치.",
        "evidence": [
            ("악보바다 원키 D", "http://www.akbobada.com/musicDetail.html?musicID=91920", "원키 D(라장조)"),
            ("마피아 악보 템포 96", "https://www.mapianist.com/sheet/137343", "Dkey[원키] · 템포 96"),
            ("chordtool 코드", "https://chordtool.com/%EC%9D%B4%EB%AC%B4%EC%A7%84/%EC%B2%AD%ED%98%BC%ED%95%98%EC%A7%80-%EC%95%8A%EC%9D%84-%EC%9D%B4%EC%9C%A0%EB%A5%BC-%EB%AA%BB-%EC%B0%BE%EC%95%98%EC%96%B4", "A D E G A7 Bm7 Em7 F#m"),
        ],
    },
    "restored-144": {  # 기억을 걷는 시간 / 넬
        "originalKey": "Eb", "timeSignature": "4/4", "timeNote": "mymusic5 악보 표기",
        "bpm": 89, "shift": 2, "bpmNote": "ezcho 89bpm",
        "stage": 1,
        "sections": [
            {"name": "Intro", "bars": [["Eb", "F"], ["Bb", "Gm7"]]},
            {"name": "Verse", "bars": [["Eb", "F"], ["Bb", "Gm7"], ["Eb", "F"], ["Gm7"]]},
            {"name": "Pre", "bars": [["Bb", "Eb"], ["F", "Bb"], ["Gm7", "Eb"], ["F"]]},
            {"name": "Chorus", "bars": [["Eb", "F"], ["Gm7"], ["Eb", "F"], ["Bb"]]},
        ],
        "stroke": "↓ · ↓↑ · ↑↓↑ (16비트, ezcho 표기)",
        "percussive": "후렴 2·4박 톡. 원곡 드럼이 단순해서 척킹이 잘 들린다.",
        "why": "Cadd9·Dsus4·G·Em7 네 코드. 오픈 코드만으로 끝나 1단계 최적.",
        "evidence": [
            ("쉬운코드 ezcho", "http://www.ezcho.com/chop/17841", "원키 Eb · 카포3(C 운지) · bpm 89 · 오픈 코드만"),
            ("mymusic5 악보", "https://www.mymusic5.com/624tabs/198978", "4/4 · 90bpm · 86마디"),
            ("코드악보(3capo)", "https://nureungi.tistory.com/20", "Cadd9 Dsus4 G Em7 진행"),
        ],
    },
    "restored-146": {
        "percussiveReady": True,  # Way Back Home / Shaun
        "originalKey": "Bb", "timeSignature": "4/4", "timeNote": "hooktheory·guitarworld 표기",
        "bpm": 100, "shift": 2, "bpmNote": "hooktheory 100bpm",
        "stage": 1,
        "sections": [
            {"name": "Intro", "bars": [["Gm", "Eb"], ["F", "Bb"]]},
            {"name": "Verse", "bars": [["Gm", "Eb"], ["F", "Bb"], ["Gm", "Eb"], ["F", "Bb"]]},
            {"name": "Chorus", "bars": [["Gm", "Eb"], ["F", "Bb"], ["Gm", "Eb"], ["F", "Bb"]]},
        ],
        "stroke": "↓ ↓ ↑ ↓ ↓ ↑ (2·4박 강세, 8분)",
        "percussive": "2·4박을 손날로 막는 척킹이 원곡 그루브의 핵심. 처음 도전하기 좋은 곡.",
        "why": "Em–C–D–G 네 코드가 두 마디씩 무한 반복. 코드 4개·한 마디 두 코드.",
        "evidence": [
            ("Hooktheory", "https://www.hooktheory.com/theorytab/view/shaun/way-back-home", "Key Bb Major · Tempo 100 · 4/4"),
            ("guitarworld 4/4 100bpm", "https://www.guitarworld.com.cn/pu/q86828", "原调 Bb · 4/4 · 100bpm · Capo4"),
            ("knockonrecords 레슨", "https://knockonrecords.kr/584", "Em7-C-D-G 2마디 진행, 2박마다 코드 변경"),
            ("kanpu 코드표", "https://kanpu8.com/chords/way-back-home/", "key Gm play Em capo3 · Em C D G 각 2박"),
        ],
    },
    "restored-150": {  # WHAT IS LOVE / EXO
        "originalKey": "", "missing": "코드표 미확보",
    },
    "restored-151": {
        "percussiveReady": True,  # Lonely / 2NE1
        "originalKey": "E", "timeSignature": "4/4", "timeNote": "guitarworld 4/4",
        "bpm": 95, "shift": 4, "bpmNote": "guitarworld·위키 95bpm",
        "stage": 2,
        "sections": [
            {"name": "Verse", "bars": [["E", "G#m7"], ["C#m7", "B"]]},
            {"name": "Chorus", "bars": [["F#", "C#"], ["D#m", "B"], ["C#"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (95bpm 8비트)",
        "percussive": "2·4박 톡. 원곡은 현악 중심이라 가볍게 치는 게 좋다.",
        "why": "E키지만 C·Em7·Am7·G·D·A로 8비트 반주가 단순하다. 여성 원곡이라 4키 내린다.",
        "evidence": [
            ("guitarworld 4/4 95bpm", "https://www.guitarworld.com.cn/pu/q130292", "原调 E · 4/4 · 95bpm"),
            ("위키백과 키·BPM", "https://en.wikipedia.org/wiki/Lonely_(2NE1_song)", "E major · 95 BPM"),
            ("코드악보", "https://playguitar.tistory.com/72", "C Em7 Am7 G · Chorus D A Bm G"),
        ],
    },
    "restored-100": {"originalKey": "", "missing": "코드표 미확보"},
    "restored-102": {
        "percussiveReady": True,  # 눈이 오잖아 / 이무진
        "originalKey": "Eb", "timeSignature": "4/4", "timeNote": "mymusic5 악보 표기",
        "bpm": 96, "shift": 2, "bpmNote": "mymusic5 96bpm",
        "stage": 3,
        "sections": [
            {"name": "Verse", "bars": [["Eb"], ["Bb"], ["G"], ["Cm"]]},
            {"name": "Pre", "bars": [["Ab"], ["Eb"], ["Dm"], ["G"]]},
            {"name": "Chorus", "bars": [["Cm"], ["Ab"], ["Eb"], ["Bb"], ["G"]]},
        ],
        "stroke": "↓ ↓↑ ↑ ↓↑ (96bpm, 후렴은 16비트)",
        "percussive": "후렴 '눈이 오잖아' 첫 박에 세게, 3·4박 컷. 겨울 버스킹용.",
        "why": "Eb키 C모양 카포3. G·Cm이 자주 나와 슬롯 2개를 쓴다.",
        "evidence": [
            ("코드악보 PDF(원키 Eb, 3capo C)", "https://patross0303.com/wp-content/uploads/2023/11/%EC%9D%B4%EB%AC%B4%EC%A7%84-%EB%88%88%EC%9D%B4-%EC%98%A4%EC%9E%96%EC%95%84-%EC%BD%94%EB%93%9C%EC%95%85%EB%B3%B4.pdf", "3Capo C Key(원키 Eb) · 마디별 코드"),
            ("mymusic5 4/4 96bpm", "https://www.mymusic5.com/ko/cholunguitar/342100", "♭3개 · 4/4 · 96bpm · 카포 3"),
        ],
    },
    "suggested-stand-by-me": {  # Stand by Me / Ben E. King (추천곡)
        "originalKey": "A", "timeSignature": "4/4", "timeNote": "Guitar Space·Lauren Bateman 코드표 표기",
        "bpm": 119, "shift": 0, "bpmNote": "ChordU 119.35bpm",
        "stage": 1,
        "sections": [
            {"name": "Intro", "bars": [["A"], ["A"], ["F#m"], ["F#m"], ["D"], ["E"], ["A"], ["A"]]},
            {"name": "Verse", "bars": [["A"], ["A"], ["F#m"], ["F#m"], ["D"], ["E"], ["A"], ["A"]]},
            {"name": "Chorus", "bars": [["A"], ["A"], ["F#m"], ["F#m"], ["D"], ["E"], ["A"], ["A"]]},
            {"name": "Interlude", "bars": [["A"], ["A"], ["F#m"], ["F#m"], ["D"], ["E"], ["A"], ["A"]]},
        ],
        "stroke": "↓ · ↓↑ · ↓↑ (119bpm, 8분 소울 비트)",
        "percussive": "2·4박에 손날로 바디를 톡 쳐 백비트를 살린다.",
        "why": "A–F#m–D–E 네 코드가 곡 전체에서 같은 순서로 반복된다(1–vi–IV–V). 원터치에서는 A·D·E만 눌러도 반주가 되고 F#m은 슬롯으로 넘긴다.",
        "evidence": [
            ("Guitar Space 코드 분석(Key A Major · 4/4 · A F#m D E)", "https://guitarspace.org/tips/stand-by-me-guitar-chords/", "Key A Major · 4/4 · A F#m D E (I–vi–IV–V)"),
            ("Lauren Bateman 코드 차트(파트별 마디 진행)", "https://www.laurenbateman.com/stand-by-me-guitar-chord-chart/", "Intro A A F#m F#m D E A A / Verse 동일 / Chorus 동일"),
            ("ChordU (119.35bpm · A F#m D E)", "https://chordu.com/chords-tabs-ben-e-king-stand-by-me-audio--id_hwZNL7QVJjE", "Tempo 119.35bpm · A F#m D E 반복"),
        ],
    },
}

# 남자키 변환 기본값(반음): 여성 보컬 원곡 -4, 남성 보컬 원곡 -2 (곡별 shift가 우선)
FEMALE_ORIGINAL = {
    # 원곡 보컬이 여성인 곡 → 남자키 -5반음(2026-11-22 사용자 기준)
    "verified-002", "verified-007", "verified-010",
    "restored-096", "restored-119", "restored-130", "restored-131", "restored-132", "restored-151",
}
