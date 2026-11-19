import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/examples/jsm/postprocessing/GTAOPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';

/**
 * The "photographed miniature" look:
 *   render → GTAO (contact shadows) → bloom (glass highlights)
 *   → tilt-shift blur (sharp band around the subject) → ACES tone map
 *   → vignette + film grain.
 * `quality` 0 drops AO and tilt-shift for slow machines.
 */

const TiltShift = {
  uniforms: {
    tDiffuse: { value: null as THREE.Texture | null },
    uDir: { value: new THREE.Vector2(1, 0) },
    uRes: { value: new THREE.Vector2(1, 1) },
    uFocus: { value: 0.5 }, // screen y (0 bottom → 1 top) of the sharp band
    uBand: { value: 0.22 }, // half-height of the sharp band
    uAmount: { value: 2.2 }, // max blur radius in px (scaled by DPR outside)
  },
  vertexShader: /* glsl */ `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse; uniform vec2 uDir; uniform vec2 uRes;
    uniform float uFocus; uniform float uBand; uniform float uAmount;
    varying vec2 vUv;
    void main(){
      float d = max(0.0, abs(vUv.y - uFocus) - uBand);
      float r = clamp(d * 3.0, 0.0, 1.0) * uAmount;
      if (r < 0.05) { gl_FragColor = texture2D(tDiffuse, vUv); return; }
      vec2 step = uDir / uRes * r;
      vec4 c = texture2D(tDiffuse, vUv) * 0.2270270270;
      c += texture2D(tDiffuse, vUv + step * 1.3846153846) * 0.3162162162;
      c += texture2D(tDiffuse, vUv - step * 1.3846153846) * 0.3162162162;
      c += texture2D(tDiffuse, vUv + step * 3.2307692308) * 0.0702702703;
      c += texture2D(tDiffuse, vUv - step * 3.2307692308) * 0.0702702703;
      gl_FragColor = c;
    }`,
};

const Finish = {
  uniforms: {
    tDiffuse: { value: null as THREE.Texture | null },
    uTime: { value: 0 },
    uVignette: { value: 0.18 },
    uGrain: { value: 0.018 },
  },
  vertexShader: /* glsl */ `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse; uniform float uTime; uniform float uVignette; uniform float uGrain;
    varying vec2 vUv;
    float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
    void main(){
      vec4 c = texture2D(tDiffuse, vUv);
      vec2 q = vUv - 0.5;
      float v = smoothstep(0.85, 0.2, length(q * vec2(1.0, 1.15)));
      c.rgb *= mix(1.0 - uVignette, 1.0, v);
      float g = hash(vUv * 1000.0 + fract(uTime * 7.0)) - 0.5;
      // Grain mostly in the mids, like film.
      float l = dot(c.rgb, vec3(0.299, 0.587, 0.114));
      c.rgb += g * uGrain * (1.0 - abs(l - 0.5) * 1.4);
      gl_FragColor = c;
    }`,
};

export class Post {
  composer: EffectComposer;
  private gtao: GTAOPass | null = null;
  private bloom: UnrealBloomPass;
  private tiltH: ShaderPass;
  private tiltV: ShaderPass;
  private finish: ShaderPass;
  private renderer: THREE.WebGLRenderer;
  /** Objects hidden while GTAO renders its normal/depth buffers (glass, snow…). */
  aoExclude: THREE.Object3D[] = [];

  constructor(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.PerspectiveCamera, quality: 0 | 1) {
    this.renderer = renderer;
    const size = renderer.getSize(new THREE.Vector2());
    const target = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: quality ? 4 : 0 });
    this.composer = new EffectComposer(renderer, target);
    this.composer.addPass(new RenderPass(scene, camera));

    if (quality) {
      const gtao = new GTAOPass(scene, camera, size.x, size.y);
      gtao.updateGtaoMaterial({ radius: 0.12, distanceExponent: 1.2, thickness: 1.0, scale: 1.0, samples: 12 });
      gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 12 });
      gtao.blendIntensity = 0.85;
      // Hide transparent things during the AO pre-passes only.
      const render = gtao.render.bind(gtao);
      gtao.render = (r, w, rd, dt, mask) => {
        const vis = this.aoExclude.map((o) => o.visible);
        this.aoExclude.forEach((o) => (o.visible = false));
        // GTAO renders its own normal/depth first, then composites onto readBuffer.
        const origRender = r.render.bind(r);
        let restored = false;
        r.render = (s, cam) => {
          origRender(s, cam);
          if (!restored) { /* first internal render = normals+depth */ restored = true; this.aoExclude.forEach((o, i) => (o.visible = vis[i])); }
        };
        try { render(r, w, rd, dt, mask); } finally { r.render = origRender; this.aoExclude.forEach((o, i) => (o.visible = vis[i])); }
      };
      this.composer.addPass(gtao);
      this.gtao = gtao;
    }

    this.bloom = new UnrealBloomPass(new THREE.Vector2(size.x, size.y), 0.16, 0.4, 0.95);
    this.composer.addPass(this.bloom);

    this.tiltH = new ShaderPass(TiltShift);
    this.tiltV = new ShaderPass(TiltShift);
    this.tiltV.uniforms.uDir.value = new THREE.Vector2(0, 1);
    this.tiltH.enabled = this.tiltV.enabled = quality === 1;
    this.composer.addPass(this.tiltH);
    this.composer.addPass(this.tiltV);

    this.composer.addPass(new OutputPass());
    this.finish = new ShaderPass(Finish);
    this.composer.addPass(this.finish);
  }

  setSize(w: number, h: number) {
    this.composer.setPixelRatio(this.renderer.getPixelRatio());
    this.composer.setSize(w, h);
    const pr = this.renderer.getPixelRatio();
    for (const p of [this.tiltH, this.tiltV]) p.uniforms.uRes.value.set(w * pr, h * pr);
    this.tiltH.uniforms.uAmount.value = this.tiltV.uniforms.uAmount.value = 2.4 * pr;
  }

  /** Sharp band centred on screen-space y (0 = bottom, 1 = top). */
  setFocus(y: number, band: number, amount = 1) {
    for (const p of [this.tiltH, this.tiltV]) {
      p.uniforms.uFocus.value = y;
      p.uniforms.uBand.value = band;
    }
    const pr = this.renderer.getPixelRatio();
    this.tiltH.uniforms.uAmount.value = this.tiltV.uniforms.uAmount.value = 2.4 * pr * amount;
  }

  render(t: number) {
    this.finish.uniforms.uTime.value = t;
    this.composer.render();
  }

  get hasAO() {
    return !!this.gtao;
  }
}
