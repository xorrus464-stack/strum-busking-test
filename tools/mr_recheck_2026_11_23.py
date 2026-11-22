#!/usr/bin/env python3
"""STRUM 4곡 순수 MR 기준 코드·BPM·키·마디 재검수 (2026-11-23, seed v18).

대상과 음원
  verified-017  나는 버려질 장난감       media/toy-mr.mp3      (4:01.74, 128k)
  verified-021  날씨가 좋고 바람도 좋아  media/weather-mr.mp3  (3:09.02, 128k)
  playlist-072  커피(Coffee)            media/coffee-mr.mp3   (3:02.13, 128k)
  playlist-173  괜히 보고 싶은 사실…     media/jehoda-mr.mp3   (3:55.78)

MR(보컬 제거 반주)에서 뽑는 값
  - 템포: 온셋 포락선(퍼커시브 성분) 위에 일정 간격 격자를 세우고 BPM·위상을 전수 탐색해
          격자 위 온셋 세기가 최대가 되는 BPM을 찾는다(0.02 BPM 단위) + 구간별 자기상관 교차 확인
  - 조성: CQT 크로마 평균 → 크럼한슬러-슈무클러 프로파일 24조 상관(전체·전반·후반)
  - 저역 근음: 220Hz 로우패스 → STFT(8192) 45~200Hz 최대 피크 → 음정 → 8프레임 중앙값
  - 마디 코드: CQT 크로마 + 코드 템플릿(3화음·7·M7·m7·sus4·dim) 코사인 + 저역 근음 가중
  - 마디 안 절반(2박) 코드도 함께 뽑아 2박 화성 리듬을 확인
  - 악보 대조: (a) 악보 구간 이름의 시각을 그대로 쓴 1:1 대조, (b) 마디 격자 위상을 다시 맞춘 대조

출력: tmp/mr_recheck/<id>.json (측정 원자료 + 대조 결과)
실행: python3 tools/mr_recheck_2026_11_23.py [id ...]
"""
import collections
import json
import pathlib
import re
import sys

import librosa
import numpy as np
from scipy.signal import butter, sosfilt

BASE = pathlib.Path(__file__).resolve().parents[1]
OUT = BASE / 'tmp' / 'mr_recheck'
SR = 22050
HOP = 512
NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
PX = {n: i for i, n in enumerate(NAMES)}
PX.update({'C#': 1, 'D#': 3, 'F#': 6, 'G#': 8, 'A#': 10, 'Cb': 11, 'Fb': 4})
QUAL = {'': (0, 4, 7), 'm': (0, 3, 7), '7': (0, 4, 7, 10), 'maj7': (0, 4, 7, 11),
        'm7': (0, 3, 7, 10), 'dim': (0, 3, 6), 'sus4': (0, 5, 7), 'm7b5': (0, 3, 6, 10)}
KEY_MAJ = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KEY_MIN = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

TARGETS = {
    # id: (MR 음원, 재검수 BPM 범위, 악보가 적어 둔 BPM)
    'verified-017': ('media/toy-mr.mp3', (46, 52), 49),
    'verified-021': ('media/weather-mr.mp3', (86, 94), 90),
    'playlist-072': ('media/coffee-mr.mp3', (94, 102), 99),
    'playlist-173': ('media/jehoda-mr.mp3', (70, 80), 76),
}


def template(pc, q):
    ivs = QUAL[q]
    w = [1.0, 0.95, 0.85] if len(ivs) == 3 else [1.0, 0.9, 0.8, 0.7]
    v = np.zeros(12)
    for iv, ww in zip(ivs, w):
        v[(pc + iv) % 12] = max(v[(pc + iv) % 12], ww)
    return v / np.linalg.norm(v)


TEMPLATES = [(pc, q, template(pc, q)) for pc in range(12) for q in QUAL]


def parse_chord(label):
    m = re.match(r'^([A-G](?:#|b)?)(.*)$', label.replace('♭', 'b').replace('♯', '#'))
    if not m:
        return None, ''
    root, rest = PX.get(m.group(1)), m.group(2)
    q = ''
    for cand in ('maj7', 'm7b5', 'dim', 'sus4', 'm7', 'add9', '7', 'm'):
        if rest.startswith(cand):
            q = cand
            break
    return root, q


def key_rank(chroma):
    x = chroma / (np.linalg.norm(chroma) + 1e-9)
    r = []
    for root in range(12):
        for mode, prof in (('장조', KEY_MAJ), ('단조', KEY_MIN)):
            p = np.roll(np.array(prof), root)
            r.append((round(float(np.dot(x, p / np.linalg.norm(p))), 3), NAMES[root] + mode))
    return sorted(r, reverse=True)


class Track:
    def __init__(self, path):
        self.path = path
        self.y, _ = librosa.load(path, sr=SR, mono=True)
        self.dur = len(self.y) / SR
        self.perc = librosa.effects.percussive(self.y, margin=3.0)
        self.C = librosa.util.normalize(librosa.feature.chroma_cqt(y=self.y, sr=SR, hop_length=HOP),
                                        axis=0, norm=np.inf, threshold=1e-6)
        self.tc = librosa.times_like(self.C, sr=SR, hop_length=HOP)
        self.bass_pc, self.bass_t, self.bass_mag = self._bass()
        self.onset = librosa.onset.onset_strength(y=self.perc, sr=SR, hop_length=HOP)

    def _bass(self):
        yb = sosfilt(butter(8, 220 / (SR / 2), btype='low', output='sos'), self.y)
        S = np.abs(librosa.stft(yb, n_fft=8192, hop_length=HOP))
        f = librosa.fft_frequencies(sr=SR, n_fft=8192)
        bi = np.where((f >= 45) & (f <= 200))[0]
        pcs = np.zeros(S.shape[1], int)
        mag = np.zeros(S.shape[1])
        for j in range(S.shape[1]):
            k = int(np.argmax(S[bi, j]))
            pcs[j] = int(round(librosa.hz_to_midi(f[bi[k]]))) % 12
            mag[j] = S[bi[k], j]
        sm = np.array([collections.Counter(pcs[max(0, i - 4):i + 5]).most_common(1)[0][0]
                       for i in range(len(pcs))])
        return sm, librosa.times_like(S, sr=SR, hop_length=HOP), mag

    def tempo(self, lo, hi):
        """온셋 격자 전수 탐색(0.02 BPM) + 30초 창 자기상관 교차 확인."""
        t = np.arange(len(self.onset)) / (SR / HOP)
        best = []
        for bpm in np.arange(lo, hi, 0.02):
            period = 60.0 / bpm
            top = 0.0
            for ph in np.arange(0, period, 0.01):
                idx = (np.arange(ph, t[-1], period) * (SR / HOP)).astype(int)
                idx = idx[idx < len(self.onset)]
                top = max(top, float(self.onset[idx].mean()))
            best.append((top, round(float(bpm), 2)))
        best.sort(reverse=True)
        wins = []
        fps = SR / HOP
        for w0 in np.arange(0, max(self.dur - 30, 1), 30):
            seg = self.onset[int(w0 * fps):int((w0 + 30) * fps)]
            ac = librosa.autocorrelate(seg - seg.mean(), max_size=int(2.6 * fps))
            ac /= (ac[0] + 1e-9)
            lo_i, hi_i = int(0.30 * fps), int(1.60 * fps)
            k = int(np.argmax(ac[lo_i:hi_i])) + lo_i
            a, b, c = ac[k - 1], ac[k], ac[k + 1]
            d = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
            wins.append({'t': int(w0), 'bpm': round(float(60 * fps / (k + d)), 2)})
        return {'fit': best[:3], 'windows': wins}

    def chord(self, t0, t1):
        a, b = int(np.searchsorted(self.tc, t0)), max(int(np.searchsorted(self.tc, t1)), 1)
        ch = np.median(self.C[:, a:b], axis=1)
        ch = ch / (np.linalg.norm(ch) + 1e-9)
        ba, bb = int(np.searchsorted(self.bass_t, t0)), max(int(np.searchsorted(self.bass_t, t1)), 1)
        cnt = collections.Counter(self.bass_pc[ba:bb]).most_common(3)
        total = max(bb - ba, 1)
        scored = []
        for pc, q, v in TEMPLATES:
            scored.append((round(float(np.dot(ch, v)) + (0.10 if pc == cnt[0][0] else 0.0), 3), pc, q))
        scored.sort(key=lambda x: -x[0])
        return {
            'chord': NAMES[scored[0][1]] + scored[0][2],
            'score': scored[0][0],
            'alt': [NAMES[p] + q for _, p, q in scored[1:3]],
            'bass': [(NAMES[p], round(n / total, 2)) for p, n in cnt],
            'next': [(NAMES[p] + q, s) for s, p, q in scored[1:4]],
        }


def chart_of(sid):
    songs = json.loads((BASE / 'data/songs.seed.json').read_text(encoding='utf-8'))
    return [s for s in songs if s['id'] == sid][0]


def sec_times(sec):
    ts = re.findall(r'(\d+):(\d\d)', sec['name'])
    if len(ts) < 2:
        return None, None
    return int(ts[0][0]) * 60 + int(ts[0][1]), int(ts[1][0]) * 60 + int(ts[1][1])


def analyze(sid):
    rel, (lo, hi), old_bpm = TARGETS[sid]
    tr = Track(BASE / rel)
    tempo = tr.tempo(lo, hi)
    bpm = tempo['fit'][0][1]
    bar = 4 * 60 / bpm
    song = chart_of(sid)
    chart = song['chart']

    keys = {
        'all': key_rank(tr.C.mean(axis=1))[:4],
        'first_half': key_rank(tr.C[:, :tr.C.shape[1] // 2].mean(axis=1))[:3],
        'second_half': key_rank(tr.C[:, tr.C.shape[1] // 2:].mean(axis=1))[:3],
    }
    windows = []
    for t0 in np.arange(0, max(tr.dur - 12, 1), 12):
        a, b = int(np.searchsorted(tr.tc, t0)), int(np.searchsorted(tr.tc, min(t0 + 12, tr.dur)))
        windows.append({'t': int(t0), 'key': key_rank(np.median(tr.C[:, a:b], axis=1))[0]})

    # (a) 악보 구간 시각 그대로 1:1 대조
    rows = []
    for sec in chart['sections']:
        t0, t1 = sec_times(sec)
        n = len(sec['bars'])
        if t0 is None or n == 0:
            continue
        span = (t1 - t0) / n if t1 else bar
        for j, bar_cells in enumerate(sec['bars']):
            a = t0 + j * span
            b = a + span
            if b > tr.dur:
                break
            m = tr.chord(a, b)
            roots = [parse_chord(c['orig'])[0] for c in bar_cells]
            rows.append({
                'section': sec['name'], 'bar': len(rows) + 1, 't': round(a, 1), 'span': round(span, 2),
                'chart': [c['orig'] for c in bar_cells], 'meas': m['chord'], 'score': m['score'],
                'bass': m['bass'], 'match': parse_chord(m['chord'])[0] in roots,
            })
    hit = sum(r['match'] for r in rows)

    # (b) 마디 격자 위상을 다시 맞춘 대조(악보 마디 수 그대로)
    allbars = [bar_cells for sec in chart['sections'] for bar_cells in sec['bars']]
    roots = [[parse_chord(c['orig'])[0] for c in b] for b in allbars]
    best = None
    for ph in np.arange(0, bar, 0.1):
        n = h = 0
        for i, r in enumerate(roots):
            t0 = ph + i * bar
            if t0 + bar > tr.dur:
                break
            n += 1
            h += parse_chord(tr.chord(t0, t0 + bar)['chord'])[0] in r
        if n > 10 and (best is None or h / n > best[0]):
            best = (round(h / n, 3), round(float(ph), 2), h, n)

    # 측정 마디(코드 1개/마디) 전체
    measured = []
    ph = max(0.0, (0.05 if sid == 'verified-017' else 0.0))
    nbars = int(round((tr.dur - ph) / bar))
    for i in range(nbars):
        t0 = ph + i * bar
        t0 = 0.0 + i * bar if sid != 'verified-017' else 0.05 + i * bar
        m = tr.chord(t0, t0 + bar)
        h = tr.chord(t0, t0 + bar / 2)
        h2 = tr.chord(t0 + bar / 2, t0 + bar)
        measured.append({'bar': i + 1, 't': round(t0, 2), **m,
                         'halves': [h['chord'], h2['chord']],
                         'halfBass': [h['bass'][0][0] if h['bass'] else '', h2['bass'][0][0] if h2['bass'] else '']})

    out = {
        'id': sid, 'title': song['title'], 'file': rel, 'duration': round(tr.dur, 2),
        'chartBpm': old_bpm, 'chartKey': song['key'], 'measuredBpm': bpm,
        'tempo': tempo, 'barLength': round(bar, 3), 'barCount': nbars,
        'keys': keys, 'keyWindows': windows,
        'compareSectionTimes': {'rows': rows, 'hit': hit, 'n': len(rows)},
        'compareAligned': {'rate': best[0], 'phase': best[1], 'hit': best[2], 'n': best[3]},
        'measuredBars': measured,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{sid}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"{sid} {song['title'][:22]}: dur {out['duration']}s bpm {old_bpm}→{bpm} "
          f"(후보 {tempo['fit']}) bar {out['barLength']}s × {nbars} "
          f"key {song['key']}→{keys['all'][0][1]}({keys['all'][0][0]}) "
          f"구간시각 대조 {hit}/{len(rows)} 정렬 대조 {best[2]}/{best[3]}")
    return out


if __name__ == '__main__':
    for sid in (sys.argv[1:] or list(TARGETS)):
        analyze(sid)
