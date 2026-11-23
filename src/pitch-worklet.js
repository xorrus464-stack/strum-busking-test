/* STRUM — MR(MP3) 실시간 키 조절용 피치 시프터 (AudioWorklet)
 *
 * 목표: 재생 속도(템포)는 그대로 두고 음높이만 바꾼다. 노래방의 '키 올리기/내리기'와 같다.
 * 방식: 그래뉼러(granular) 방식. 입력을 버퍼에 쓰면서, 두 개의 읽기 헤드가
 *       ratio 배속으로 읽고, 각 헤드의 사인제곱 창(sin²)을 겹쳐 합산한다.
 *       sin²(x) + sin²(x+90°) = 1 이므로 창 합이 항상 1 → 음량이 일정하다.
 *       헤드가 버퍼를 한 바퀴 도는 주기마다 이어붙임(splice)이 생기는데,
 *       두 헤드를 반 주기 어긋나게 두어 이음매를 서로 가린다.
 * ratio = 2^(반음/12). ratio 가 1에 아주 가까우면(dry) 원음을 그대로 통과시킨다
 *       (같은 신호를 두 딜레이로 겹치면 콤 필터가 생기므로).
 *
 * 앱에서는 audioWorklet.addModule('src/pitch-worklet.js') 로 불러 쓴다.
 */
const GRAIN_SECONDS = 0.09;   // 90ms — 노래 반주에 무난한 입자 길이

class StrumPitchProcessor extends AudioWorkletProcessor {
  static get parameterDescriptors() {
    return [{ name: 'ratio', defaultValue: 1, minValue: 0.5, maxValue: 2, automationRate: 'k-rate' }];
  }

  constructor() {
    super();
    this.grain = Math.max(256, Math.round(sampleRate * GRAIN_SECONDS));
    this.size = 1;
    while (this.size < this.grain * 4) this.size *= 2;
    this.mask = this.size - 1;
    this.buffers = [];
    this.w = 0;         // 쓰기 위치(샘플 단위 누적)
    this.d = 0;         // 읽기 지연(샘플). 0..grain 사이를 오간다
    this.ratio = 1;
    this.port.onmessage = (e) => {
      const m = e.data || {};
      if (m.type === 'reset') this.reset();
      if (m.type === 'ratio' && typeof m.value === 'number') this.ratio = m.value;
    };
  }

  reset() {
    this.w = 0;
    this.d = 0;
    for (const b of this.buffers) b.fill(0);
  }

  buffer(ch) {
    if (!this.buffers[ch]) this.buffers[ch] = new Float32Array(this.size);
    return this.buffers[ch];
  }

  read(buf, pos) {
    const i = Math.floor(pos);
    const frac = pos - i;
    const a = buf[i & this.mask];
    const b = buf[(i + 1) & this.mask];
    return a + (b - a) * frac;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    if (!output || !output.length) return true;
    const n = output[0].length;
    const params = parameters.ratio;
    const target = params && params.length ? params[0] : 1;

    if (!input || !input.length) {
      for (const ch of output) ch.fill(0);
      return true;
    }

    const dry = Math.abs(target - 1) < 0.003;
    const ratio = this.ratio;
    const grain = this.grain;
    const half = grain * 0.5;

    for (let c = 0; c < output.length; c++) {
      const inCh = input[c] || input[0];
      const outCh = output[c];
      const buf = this.buffer(c);
      let w = this.w;
      let d = this.d;
      for (let i = 0; i < n; i++) {
        const x = inCh[i];
        buf[w & this.mask] = x;
        if (dry) {
          outCh[i] = x;
        } else {
          d += 1 - ratio;
          d -= Math.floor(d / grain) * grain;      // 0..grain 로 접기
          const d1 = d;
          const d2 = d + half >= grain ? d + half - grain : d + half;
          const g1 = Math.sin(Math.PI * d1 / grain);
          const g2 = Math.sin(Math.PI * d2 / grain);
          const s1 = this.read(buf, w - d1);
          const s2 = this.read(buf, w - d2);
          outCh[i] = g1 * g1 * s1 + g2 * g2 * s2;
        }
        w++;
      }
      if (c === output.length - 1) {
        this.w = w;
        this.d = d;
      }
    }
    return true;
  }
}

registerProcessor('strum-pitch', StrumPitchProcessor);
