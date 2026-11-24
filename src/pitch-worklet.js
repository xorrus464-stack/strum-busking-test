/* STRUM — MR(MP3) 실시간 키 조절용 피치 시프터 (AudioWorklet 래퍼, v22)
 *
 * 알고리즘 자체는 src/pitch-grain.js 에 있고, 여기서는 AudioWorkletProcessor 로 감싼다.
 *
 * ★ v22에서 고친 치명적 버그 (2026-11-25)
 *   앱은 `node.parameters.get('ratio').value = ratio` 로 AudioParam 만 바꿨는데,
 *   워클릿은 실제로는 `this.ratio`(=1, port 메시지로만 바뀜)로 읽고 있었다.
 *   그래서 키를 올려도 소리는 그대로였고, `dry` 판정만 AudioParam 값을 보고
 *   엉뚱하게 45ms 지연된 0키 소리를 내고 있었다.
 *   → 이제 AudioParam 값(target)을 그대로 ratio 로 쓴다. port 'ratio' 메시지는
 *     폴백 경로·구버전 앱과의 호환을 위해 '덮어쓰기(override)' 로만 남겨 둔다.
 */
import './pitch-grain.js?v=22';

const Core = globalThis.StrumPitchCore;

class StrumPitchProcessor extends AudioWorkletProcessor {
  static get parameterDescriptors() {
    return [{ name: 'ratio', defaultValue: 1, minValue: 0.5, maxValue: 2, automationRate: 'k-rate' }];
  }

  constructor() {
    super();
    this.shifter = new Core.GrainShifter(sampleRate, 2);
    this.override = null;
    this.port.onmessage = (e) => {
      const m = e.data || {};
      if (m.type === 'reset') this.shifter.reset();
      if (m.type === 'ratio' && typeof m.value === 'number' && m.value > 0) this.override = m.value;
    };
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    if (!output || !output.length) return true;
    const frames = output[0].length;
    if (!input || !input.length) {
      for (const ch of output) ch.fill(0);
      return true;
    }
    const p = parameters.ratio;
    let target = p && p.length ? p[0] : 1;
    if (this.override != null) target = this.override;
    this.shifter.process(input, output, frames, target);
    return true;
  }
}

registerProcessor('strum-pitch', StrumPitchProcessor);
