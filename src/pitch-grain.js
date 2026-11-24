/* STRUM — MR(MP3) 실시간 키 조절용 피치 시프터 핵심 알고리즘 (2026-11-25, v22)
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
 * 이 파일 하나를 두 곳에서 같이 쓴다.
 *  1) AudioWorklet  : src/pitch-worklet.js 가 `import './pitch-grain.js?v=22'` 로 불러온다.
 *  2) ScriptProcessor 폴백 : app.js 가 <script> 로 불러 window.StrumPitchCore 를 쓴다.
 *     (안드로이드 WebView·인앱 브라우저처럼 AudioWorklet 이 없는 환경용)
 *
 * 쓰는 법
 *   const shifter = new StrumPitchCore.GrainShifter(sampleRate, 2);
 *   shifter.process(inputChannels, outputChannels, frames, ratio);
 *     inputChannels  : Float32Array[] (채널별 입력, 없으면 null)
 *     outputChannels : Float32Array[] (채널별 출력, 미리 잡혀 있는 버퍼)
 *     ratio          : 이번 블록에 쓸 피치 비율(생략하면 이전 값 유지)
 */
(function (root) {
  'use strict';

  var GRAIN_SECONDS = 0.09;   // 90ms — 노래 반주에 무난한 입자 길이
  var DRY_EPS = 0.003;        // ratio 가 이만큼 1에 가까우면 원음 통과

  function GrainShifter(sampleRate, channels) {
    this.sampleRate = sampleRate || 44100;
    this.channels = channels || 2;
    this.grain = Math.max(256, Math.round(this.sampleRate * GRAIN_SECONDS));
    this.size = 1;
    while (this.size < this.grain * 4) this.size *= 2;
    this.mask = this.size - 1;
    this.buffers = [];
    this.w = 0;        // 쓰기 위치(샘플 단위 누적)
    this.d = 0;        // 읽기 지연(샘플). 0..grain 사이를 오간다
    this.ratio = 1;
  }

  GrainShifter.prototype.reset = function () {
    this.w = 0;
    this.d = 0;
    for (var i = 0; i < this.buffers.length; i++) this.buffers[i].fill(0);
  };

  GrainShifter.prototype.buffer = function (ch) {
    if (!this.buffers[ch]) this.buffers[ch] = new Float32Array(this.size);
    return this.buffers[ch];
  };

  GrainShifter.prototype.read = function (buf, pos) {
    var i = Math.floor(pos);
    var frac = pos - i;
    var a = buf[i & this.mask];
    var b = buf[(i + 1) & this.mask];
    return a + (b - a) * frac;
  };

  /* 이번 블록(프레임 수)을 처리해 output 에 채운다.
     ratio 는 '이번 블록의 목표 비율'이다. 워클릿에서는 AudioParam 값을, 폴백에서는
     버튼으로 지정한 값을 그대로 넘겨 준다 — 두 경로 모두 같은 알고리즘을 쓴다. */
  GrainShifter.prototype.process = function (input, output, frames, ratio) {
    if (typeof ratio === 'number' && isFinite(ratio) && ratio > 0) this.ratio = ratio;
    var r = this.ratio;
    var dry = Math.abs(r - 1) < DRY_EPS;
    var grain = this.grain;
    var half = grain * 0.5;
    var mask = this.mask;
    var outN = output.length;

    for (var c = 0; c < outN; c++) {
      var inCh = input && (input[c] || input[0]);
      var outCh = output[c];
      if (!outCh) continue;
      var buf = this.buffer(c);
      var w = this.w;
      var d = this.d;
      for (var i = 0; i < frames; i++) {
        var x = inCh ? inCh[i] : 0;
        buf[w & mask] = x;
        if (dry) {
          outCh[i] = x;
        } else {
          d += 1 - r;
          if (d >= grain || d < 0) d -= Math.floor(d / grain) * grain;   // 0..grain 로 접기
          var d1 = d;
          var d2 = d + half >= grain ? d + half - grain : d + half;
          var s1 = this.read(buf, w - d1);
          var s2 = this.read(buf, w - d2);
          var g1 = Math.sin(Math.PI * d1 / grain);
          var g2 = Math.sin(Math.PI * d2 / grain);
          outCh[i] = g1 * g1 * s1 + g2 * g2 * s2;
        }
        w++;
      }
      if (c === outN - 1) {
        this.w = w;
        this.d = d;
      }
    }
  };

  /* ScriptProcessor 폴백용 노드 — AudioWorklet 을 못 쓰는 브라우저에서 같은 알고리즘을
     메인 스레드 오디오 콜백으로 돌린다. node.__ratio 를 바꾸면 다음 블록부터 반영된다. */
  function createScriptPitchNode(ctx, frames) {
    var node = ctx.createScriptProcessor(frames || 2048, 2, 2);
    var shifter = new GrainShifter(ctx.sampleRate, 2);
    node.__ratio = 1;
    node.__shifter = shifter;
    node.onaudioprocess = function (e) {
      var out = e.outputBuffer;
      var inp = e.inputBuffer;
      if (!out) return;
      var n = out.length;
      var output = [];
      var input = [];
      for (var c = 0; c < out.numberOfChannels; c++) {
        output.push(out.getChannelData(c));
        input.push(inp && inp.numberOfChannels
          ? (c < inp.numberOfChannels ? inp.getChannelData(c) : inp.getChannelData(0))
          : null);
      }
      shifter.process(input, output, n, node.__ratio);
    };
    node.__reset = function () { shifter.reset(); };
    return node;
  }

  root.StrumPitchCore = {
    GrainShifter: GrainShifter,
    createScriptPitchNode: createScriptPitchNode,
    GRAIN_SECONDS: GRAIN_SECONDS
  };

  /* AudioWorklet 쪽(모듈)은 window/self 가 없어도 되도록 전역 한 곳에만 붙인다. */
})(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this));
