/**
 * Shadow plays: silhouettes moving behind frosted glass, one per window.
 * Each play draws into an <svg> 400 units tall and PW wide (the glass's
 * shape) and returns step(t) for t in seconds. Everything is one shade of ink
 * under one soft blur, so it reads as shadows on the same pane. Every play
 * loops without a cut: whatever leaves comes back, whatever arrives was
 * already on its way.
 */
const NS = 'http://www.w3.org/2000/svg';
export const el = <K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number>, parent: Element) => {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  parent.appendChild(e);
  return e;
};
const ease = (t: number) => (t < 0 ? 0 : t > 1 ? 1 : t * t * (3 - 2 * t));
const seg = (t: number, a: number, b: number) => ease((t - a) / (b - a));
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const set = (e: Element, d: string) => e.setAttribute('d', d);

export type Play = (svg: SVGSVGElement, PW: number) => (t: number) => void;

/** Two-bone reach: from root towards target with segment lengths l1, l2;
 *  the joint bends to the side `bend` (+1 / -1 across the root→target line). */
function ik(rx: number, ry: number, tx: number, ty: number, l1: number, l2: number, bend: number) {
  let dx = tx - rx, dy = ty - ry;
  let d = Math.hypot(dx, dy);
  const max = l1 + l2 - 0.01;
  if (d > max) { dx *= max / d; dy *= max / d; d = max; }
  const a = (l1 * l1 - l2 * l2 + d * d) / (2 * d);
  const h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
  const ux = dx / d, uy = dy / d;
  return { jx: rx + ux * a - uy * h * bend, jy: ry + uy * a + ux * h * bend, ex: rx + dx, ey: ry + dy };
}

/** The pane: one ink, one blur; `room` is scaled sideways so plays can be
 *  designed 300 wide whatever the glass's shape. */
function stage(svg: SVGSVGElement, PW: number) {
  svg.innerHTML = '';
  const ink = '#1c0d06';
  const id = 'soft' + Math.random().toString(36).slice(2, 8);
  const defs = el('defs', {}, svg);
  const f = el('filter', { id, x: '-20%', y: '-20%', width: '140%', height: '140%' }, defs);
  el('feGaussianBlur', { stdDeviation: 1.9 }, f);
  const shadow = el('g', { fill: ink, stroke: ink, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', filter: `url(#${id})`, opacity: 0.86 }, svg);
  const sx = PW / 300;
  const room = el('g', { transform: `scale(${sx} 1)` }, shadow);
  return { room, sx, defs, filter: `url(#${id})`, svg, shadow };
}

export interface Pose {
  x: number;            // hips
  face: 1 | -1;         // the way they face
  walk: number;         // 0 standing .. 1 walking
  ph: number;           // step phase
  lean?: number;        // forward lean (units)
  look?: number;        // head tilt: + looks up, - looks down (radians)
  hand: [number, number];   // front hand target
  hand2: [number, number];  // back hand target
  hipY?: number;        // standing hip height (default 298)
  sit?: boolean;        // sitting on a chair: thighs forward, shins down
}

/** A person in profile: legs that bend at the knee and lift their feet,
 *  a jumper with a hem, arms with elbows and hands, a head with a brow,
 *  nose, lips and chin, hair in a bun (or a headset strapped on). */
export type Hair = 'bun' | 'short' | 'long' | 'pony' | 'curly' | 'cap';
export interface Look { headset?: boolean; hair?: Hair; height?: number; build?: number; apron?: boolean }
export function person(parent: Element, opts: Look = {}) {
  const outer = el('g', {}, parent);
  const g = el('g', {}, outer);
  const hairKind: Hair = opts.hair ?? 'bun';
  const tall = opts.height ?? 1, wide = opts.build ?? 1;
  const legBack = el('path', { fill: 'none', 'stroke-width': 13 }, g);
  const shoeBack = el('path', { stroke: 'none' }, g);
  const armBack = el('path', { fill: 'none', 'stroke-width': 9 }, g);
  const handBack = el('circle', { r: 5, stroke: 'none' }, g);
  const torso = el('path', { stroke: 'none' }, g);
  const apron = opts.apron ? el('path', { stroke: 'none' }, g) : null;
  const headG = el('g', {}, g);
  const head = el('path', { stroke: 'none' }, headG);
  const hair = el('path', { stroke: 'none' }, headG);
  const strands = el('path', { fill: 'none', 'stroke-width': 1.4 }, headG);
  const visor = opts.headset ? el('path', { stroke: 'none' }, headG) : null;
  const strap = opts.headset ? el('path', { fill: 'none', 'stroke-width': 4 }, headG) : null;
  const legFront = el('path', { fill: 'none', 'stroke-width': 13.5 }, g);
  const shoeFront = el('path', { stroke: 'none' }, g);
  const armFront = el('path', { fill: 'none', 'stroke-width': 9.5 }, g);
  const handFront = el('path', { stroke: 'none' }, g);
  const GROUND = 396;
  return (p0: Pose) => {
    // hand targets are where they should land after the figure is scaled to its height
    const un = (pt: [number, number]): [number, number] => [p0.x + (pt[0] - p0.x) / tall, GROUND + (pt[1] - GROUND) / tall];
    const p = tall === 1 ? p0 : { ...p0, hand: un(p0.hand), hand2: un(p0.hand2) };
    const { x, face, walk, ph } = p;
    const lean = p.lean ?? 0;
    const bob = walk * Math.abs(Math.sin(ph)) * 3.5;
    const hipY = (p.hipY ?? 298) - bob, shY = hipY - 92;
    const X = (u: number) => x + face * u;
    const leg = (side: number) => {
      const s_ = walk * Math.sin(ph + (side > 0 ? 0 : Math.PI));
      const fx = X(2 + s_ * 18), fy = GROUND - Math.max(0, walk * Math.cos(ph + (side > 0 ? 0 : Math.PI))) * 7;
      const hx = X(side * 2), j = ik(hx, hipY, fx, fy, 50, 49, -face);
      const toe = fx + face * 15;
      return { d: `M ${hx} ${hipY} L ${j.jx} ${j.jy} L ${j.ex} ${j.ey}`,
               shoe: `M ${j.ex - face * 7} ${j.ey - 6} Q ${j.ex + face * 4} ${j.ey - 9} ${toe} ${j.ey - 1} Q ${toe + face} ${j.ey + 3} ${toe - face * 3} ${j.ey + 3} L ${j.ex - face * 8} ${j.ey + 3} Z` };
    };
    const sitLeg = (side: number) => {
      const hx = X(side * 2), kx = X(46 + side * 2), ky = hipY + 4;
      const fx = X(42 + side * 3);
      return { d: `M ${hx} ${hipY} L ${kx} ${ky} L ${fx} ${GROUND}`,
               shoe: `M ${fx - face * 6} ${GROUND - 6} Q ${fx + face * 4} ${GROUND - 9} ${fx + face * 15} ${GROUND - 1} L ${fx + face * 12} ${GROUND + 3} L ${fx - face * 7} ${GROUND + 3} Z` };
    };
    const lb = p.sit ? sitLeg(-1) : leg(-1), lf = p.sit ? sitLeg(1) : leg(1);
    set(legBack, lb.d); set(shoeBack, lb.shoe); set(legFront, lf.d); set(shoeFront, lf.shoe);
    const B = (u: number) => X(u * wide);
    set(torso, `M ${B(-5 + lean)} ${shY - 8} Q ${B(-17 + lean)} ${shY - 4} ${B(-17 + lean)} ${shY + 10} Q ${B(-19)} ${shY + 50} ${B(-15)} ${hipY - 6}
      Q ${B(-17)} ${hipY + 4} ${B(-14)} ${hipY + 9} L ${B(15)} ${hipY + 9} Q ${B(18)} ${hipY + 2} ${B(15)} ${hipY - 8}
      Q ${B(13)} ${shY + 52} ${B(18 + lean)} ${shY + 22} Q ${B(19 + lean)} ${shY + 4} ${B(10 + lean)} ${shY - 2} L ${B(6 + lean)} ${shY - 10} Z`);
    if (apron) set(apron, `M ${B(14 + lean)} ${shY + 30} L ${B(19)} ${hipY + 30} Q ${B(10)} ${hipY + 34} ${B(2)} ${hipY + 30} L ${B(4)} ${shY + 30} Z
      M ${B(4 + lean)} ${shY + 14} L ${B(-12 + lean)} ${shY + 26} L ${B(-11 + lean)} ${shY + 29} L ${B(5 + lean)} ${shY + 19} Z`);
    const hx = X(4 + lean * 1.4), hy = shY - 30;
    const P = (u: number, v: number) => `${hx + face * u} ${hy + v}`;
    set(head, `M ${P(-12, -14)} Q ${P(-2, -22)} ${P(9, -16)} Q ${P(14, -10)} ${P(13, -3)} L ${P(18, 3)} Q ${P(19, 5)} ${P(14, 6)}
      Q ${P(15, 9)} ${P(13, 10)} Q ${P(14, 13)} ${P(11, 15)} Q ${P(9, 19)} ${P(3, 19)} Q ${P(-1, 19)} ${P(-1, 24)} L ${P(-1, 31)}
      L ${P(-9, 31)} Q ${P(-10, 22)} ${P(-14, 14)} Q ${P(-17, 0)} ${P(-12, -14)} Z`);
    const cap = `M ${P(10, -12)} Q ${P(6, -24)} ${P(-6, -21)} Q ${P(-16, -18)} ${P(-17, -5)} Q ${P(-18, 4)} ${P(-14, 10)} Q ${P(-12, 2)} ${P(-11, -4)} Q ${P(-2, -14)} ${P(10, -12)} Z`;
    const sway = Math.sin(ph * 0.5) * walk * 2;
    if (hairKind === 'bun') {
      set(hair, `${cap} M ${P(-14, -14)} m ${-face * 5} 0 a 8 8 0 1 0 ${face * 0.1} 0 Z`);
      set(strands, `M ${P(-19, -12)} q ${-face * 5} 6 ${-face * 3} 12 M ${P(-16, -6)} q ${-face * 2} 7 ${-face * 1} 12`);
    } else if (hairKind === 'short') {
      set(hair, `M ${P(11, -11)} Q ${P(8, -23)} ${P(-5, -22)} Q ${P(-17, -19)} ${P(-17, -6)} Q ${P(-17, 2)} ${P(-13, 5)} Q ${P(-12, -2)} ${P(-10, -6)} Q ${P(0, -13)} ${P(11, -11)} Z`);
      set(strands, `M ${P(6, -19)} l ${face * 4} -2 M ${P(-2, -21)} l ${face * 3} -3`);
    } else if (hairKind === 'long') {
      set(hair, `${cap} M ${P(-17, -8)} Q ${P(-21 - sway, 14)} ${P(-18 - sway, 40)} L ${P(-8, 38)} Q ${P(-10, 18)} ${P(-11, 0)} Z`);
      set(strands, `M ${P(-20 - sway, 20)} q ${-face * 2} 10 ${face * 1} 20 M ${P(-14, 22)} q ${-face * 1} 8 0 16`);
    } else if (hairKind === 'pony') {
      set(hair, `${cap} M ${P(-16, -12)} Q ${P(-26, -12)} ${P(-27 - sway, 2)} Q ${P(-28 - sway, 18)} ${P(-22 - sway, 30)} Q ${P(-22, 14)} ${P(-17, -4)} Z`);
      set(strands, `M ${P(-17, -12)} l ${-face * 3} 1`);
    } else if (hairKind === 'curly') {
      let d = '';
      for (let k = 0; k < 9; k++) { const a = Math.PI * (0.05 + k * 0.13); d += `M ${P(-4 - Math.cos(a) * 15, -6 - Math.sin(a) * 16)} m ${-face * 6} 0 a 6 6 0 1 0 ${face * 0.1} 0 Z `; }
      set(hair, `${d} M ${P(-18, 0)} m ${-face * 5} 0 a 5 5 0 1 0 ${face * 0.1} 0 Z`);
      set(strands, '');
    } else {
      // a knitted cap with a turned-up brim and a bobble
      set(hair, `M ${P(13, -10)} Q ${P(10, -30)} ${P(-4, -29)} Q ${P(-18, -26)} ${P(-18, -8)} L ${P(-15, -6)} L ${P(13, -8)} Z M ${P(-4, -29)} m ${-face * 4} -3 a 4 4 0 1 0 ${face * 0.1} 0 Z`);
      set(strands, `M ${P(-17, -9)} L ${P(13, -11)}`);
    }
    if (visor && strap) {
      // a boxy visor over the eyes, sticking out past the nose, and its strap
      set(visor, `M ${P(2, -12)} L ${P(26, -11)} Q ${P(29, -10)} ${P(29, -6)} L ${P(29, 4)} Q ${P(29, 7)} ${P(26, 7)} L ${P(4, 6)} Z`);
      set(strap, `M ${P(4, -8)} Q ${P(-6, -12)} ${P(-17, -6)}`);
    }
    const look = (p.look ?? 0) * (180 / Math.PI) * -face;
    headG.setAttribute('transform', `rotate(${look} ${hx} ${hy + 22})`);
    const shF = { x: X(4 + lean), y: shY + 6 }, shB = { x: X(-6 + lean), y: shY + 6 };
    const aF = ik(shF.x, shF.y, p.hand[0], p.hand[1], 34, 33, face), aB = ik(shB.x, shB.y, p.hand2[0], p.hand2[1], 34, 33, face);
    set(armFront, `M ${shF.x} ${shF.y} L ${aF.jx} ${aF.jy} L ${aF.ex} ${aF.ey}`);
    set(armBack, `M ${shB.x} ${shB.y} L ${aB.jx} ${aB.jy} L ${aB.ex} ${aB.ey}`);
    handBack.setAttribute('cx', String(aB.ex)); handBack.setAttribute('cy', String(aB.ey));
    const hX = aF.ex, hY = aF.ey;
    set(handFront, `M ${hX - face * 5} ${hY - 4} Q ${hX + face * 4} ${hY - 6} ${hX + face * 7} ${hY} Q ${hX + face * 4} ${hY + 6} ${hX - face * 4} ${hY + 4} Z
      M ${hX} ${hY - 4} q ${face * 3} -6 ${face * 6} -5 q ${-face * 1} 4 ${-face * 4} 6 Z`);
    if (tall !== 1) g.setAttribute('transform', `translate(${x} ${GROUND}) scale(${tall}) translate(${-x} ${-GROUND})`);
    const sc = (pt: [number, number]): [number, number] => [x + (pt[0] - x) * tall, GROUND + (pt[1] - GROUND) * tall];
    return { shY: GROUND + (shY - GROUND) * tall, hipY: GROUND + (hipY - GROUND) * tall, hand: sc([aF.ex, aF.ey]), hand2: sc([aB.ex, aB.ey]) };
  };
}

/** Rest hands for a person standing at x facing `face`, arms swinging with the step. */
const restHands = (x: number, face: number, walk: number, ph: number, hipY = 298): [[number, number], [number, number]] => {
  const sw = walk * Math.sin(ph) * 14;
  return [[x + face * (6 + sw), hipY + 2], [x + face * (-6 - sw), hipY]];
};

// ---------------------------------------------------------------- Squirrels and Seeds
/** Someone carries a box to the shelves, slides it in and shoves it along
 *  out of sight, takes out their phone to note it down, then goes for the next. */
export const boxesPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  const shelves = el('g', {}, room);
  for (const y of [150, 235, 320]) el('rect', { x: 186, y, width: 112, height: 7, stroke: 'none' }, shelves);
  el('rect', { x: 291, y: 110, width: 8, height: 290, stroke: 'none' }, shelves);
  el('rect', { x: 188, y: 110, width: 5, height: 290, stroke: 'none' }, shelves);
  for (const [x, y, w, h] of [[200, 118, 30, 32], [200, 292, 32, 28]]) el('rect', { x, y, width: w, height: h, rx: 2, stroke: 'none' }, shelves);
  for (const [x, w, h] of [[238, 14, 22], [256, 12, 18], [272, 14, 24]]) {
    el('rect', { x, y: 150 - h, width: w, height: h, rx: 4, stroke: 'none' }, shelves);
    el('rect', { x: x - 1, y: 150 - h - 4, width: w + 2, height: 5, rx: 1, stroke: 'none' }, shelves);
  }
  for (let k = 0; k < 4; k++) el('rect', { x: 198 + (k % 2) * 2, y: 235 - 7 * (k + 1), width: 40, height: 6, rx: 3, stroke: 'none' }, shelves);
  for (const x of [244, 258, 272]) el('rect', { x, y: 302, width: 11, height: 18, rx: 2, stroke: 'none' }, shelves);
  const box = el('path', { stroke: 'none' }, room);
  const who = person(room, { hair: 'short', build: 1.08 });
  // a phone: just its shape, held low in both hands, a thumb tapping at it
  const phone = el('rect', { width: 8, height: 14, rx: 1.8, stroke: 'none' }, room);
  const thumb = el('path', { fill: 'none', 'stroke-width': 3.2 }, room);
  const LOOP = 11;
  return (time: number) => {
    const t = time % LOOP;
    const walkIn = seg(t, 0, 2.4), lift = seg(t, 2.6, 3.4), slide = seg(t, 3.4, 4.0), back = seg(t, 4.2, 4.7);
    const shove = 1 - Math.pow(1 - Math.min(1, Math.max(0, (t - 3.5) / 1.4)), 3);
    const phoneUp = seg(t, 4.7, 5.6), phoneDown = seg(t, 7.8, 8.6), walkOut = seg(t, 8.7, 10.7);
    let x = lerp(-60, 150, walkIn); x = lerp(x, -80, walkOut);
    const face = t > 8.7 ? -1 : 1;
    const walk = (t < 2.4 || t > 8.7) ? 1 : 0;
    const ph = t * 7.5;
    const out = phoneUp * (1 - phoneDown);
    const shY = 206;
    const carry = t < 3.4;
    const bx = carry ? lerp(x + 16, 228, lift) : lerp(228, 360, shove);
    const by = carry ? lerp(shY + 34, 235, lift) : 235;
    const bw = 36, bh = 28, fl = 10 * (1 - slide);
    set(box, `M ${bx} ${by - bh} L ${bx + bw} ${by - bh} L ${bx + bw} ${by} L ${bx} ${by} Z
      M ${bx} ${by - bh} L ${bx - 6} ${by - bh - fl} L ${bx + 4} ${by - bh - fl * 0.9} L ${bx + 9} ${by - bh} Z
      M ${bx + bw} ${by - bh} L ${bx + bw + 6} ${by - bh - fl} L ${bx + bw - 4} ${by - bh - fl * 0.9} L ${bx + bw - 9} ${by - bh} Z`);
    const reach = lift * (1 - back);
    let hand: [number, number], hand2: [number, number];
    if (t < 4.2) {
      hand = [lerp(bx + bw - 4, bx + 30, reach), lerp(by - bh / 2, by - bh + 4, reach)];
      hand2 = [lerp(bx + 6, bx + 8, reach), lerp(by - 6, by - bh + 8, reach)];
    } else if (out > 0.01) {
      // held at the waist, below the window's meeting rail, both hands on it
      const tap = Math.sin(t * 17) * 1.4 * (t > 5.6 && t < 7.8 ? 1 : 0);
      const [r1, r2] = restHands(x, face, walk, ph);
      hand = [lerp(r1[0], x + face * 30, out), lerp(r1[1], shY + 66, out)];
      hand2 = [lerp(r2[0], x + face * 25, out), lerp(r2[1], shY + 70 + tap, out)];
    } else [hand, hand2] = restHands(x, face, walk, ph);
    const r = who({ x, face, walk, ph, lean: out * 3, look: -out * 0.5, hand, hand2 });
    const [hX, hY] = r.hand;
    const px = hX + face * 1 - 4, py = hY - 13;
    phone.setAttribute('x', String(px)); phone.setAttribute('y', String(py));
    phone.setAttribute('transform', `rotate(${face * 18} ${px + 4} ${py + 7})`);
    phone.setAttribute('opacity', String(Math.min(1, out * 1.5)));
    const tp = t > 5.6 && t < 7.8 ? Math.abs(Math.sin(t * 8.5)) : 0.4;
    set(thumb, out > 0.3 ? `M ${r.hand2[0]} ${r.hand2[1] - 3} q ${face * 3} ${-4 - tp * 3} ${face * (5 + tp * 2)} ${-6 - tp * 4}` : '');
  };
};

// ---------------------------------------------------------------- WARG
/** Someone with a controller sets a drone humming: it lifts off, wobbles,
 *  climbs and drifts away (smaller and smaller) out of the top of the glass,
 *  then comes back down and lands where it started. */
export const dronePlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  const who = person(room, { hair: 'pony', height: 0.97 });
  const ctrl = el('path', { stroke: 'none' }, room);
  const drone = el('g', {}, room);
  el('rect', { x: -16, y: -5, width: 32, height: 9, rx: 3, stroke: 'none' }, drone);        // body and battery
  el('rect', { x: -9, y: -10, width: 18, height: 6, rx: 2, stroke: 'none' }, drone);
  el('path', { d: 'M -14 0 L -34 -3 M 14 0 L 34 -3', fill: 'none', 'stroke-width': 4 }, drone); // arms
  for (const sx of [-34, 34]) el('rect', { x: sx - 4, y: -8, width: 8, height: 8, rx: 2, stroke: 'none' }, drone); // motors
  el('path', { d: 'M -10 4 L -14 12 M 10 4 L 14 12', fill: 'none', 'stroke-width': 3 }, drone);   // legs
  el('path', { d: 'M 16 -2 L 22 -16', fill: 'none', 'stroke-width': 1.5 }, drone);             // antenna
  const props = [-34, 34].map((cx) => el('ellipse', { cx, cy: -10, rx: 13, ry: 1.6, stroke: 'none' }, drone));
  const LOOP = 12;
  return (time: number) => {
    const t = time % LOOP;
    const spin = seg(t, 1.2, 2.2) * (1 - seg(t, 9.6, 10.4));       // props up to speed and back down
    const up = seg(t, 2.2, 5.6);                                    // climbing away
    const down = seg(t, 6.8, 9.6);                                  // coming back
    const away = up * (1 - down);
    const gx = 196, gy = 384;                                       // where it sits
    const x = gx + away * 40 + Math.sin(t * 2.3) * 4 * spin;
    const y = lerp(gy, -60, Math.pow(away, 0.85)) + Math.sin(t * 5.1) * 2.5 * spin * (away > 0.01 ? 1 : 0.2);
    const sc = lerp(1, 0.32, Math.pow(away, 0.7));                  // further from the glass: smaller
    const tilt = Math.sin(t * 3.1) * 6 * spin * (away > 0.02 ? 1 : 0.1);
    drone.setAttribute('transform', `translate(${x} ${y}) scale(${sc}) rotate(${tilt})`);
    props.forEach((p, i) => {
      const w = 13 * (0.35 + 0.65 * (spin > 0.05 ? 0.75 + 0.25 * Math.abs(Math.sin(t * 40 + i)) : Math.abs(Math.cos(i))));
      p.setAttribute('rx', String(spin > 0.05 ? 15 : w));
      p.setAttribute('opacity', String(spin > 0.05 ? 0.55 : 1));
    });
    // the pilot: standing to the left, controller at the chest, watching it go
    const px = 92, face = 1 as const;
    const shY = 206;
    const cx = px + 22, cy = shY + 30 + Math.sin(t * 0.9) * 1.5;
    const thumb = spin * Math.sin(t * 2.4) * 2;
    const look = Math.max(-0.1, Math.min(0.55, Math.atan2((shY - 20) - y, x - px) * 0.8)) * (spin > 0.02 ? 1 : 0.3);
    who({ x: px, face, walk: 0, ph: 0, lean: 2, look, hand: [cx + 8, cy - 2 + thumb], hand2: [cx - 6, cy + 2 - thumb] });
    set(ctrl, `M ${cx - 12} ${cy - 6} L ${cx + 14} ${cy - 6} Q ${cx + 17} ${cy - 6} ${cx + 17} ${cy - 3} L ${cx + 17} ${cy + 4}
      Q ${cx + 17} ${cy + 7} ${cx + 13} ${cy + 7} L ${cx - 11} ${cy + 7} Q ${cx - 15} ${cy + 7} ${cx - 15} ${cy + 3} L ${cx - 15} ${cy - 3} Z
      M ${cx + 10} ${cy - 6} L ${cx + 16} ${cy - 24} L ${cx + 18} ${cy - 23} L ${cx + 13} ${cy - 6} Z`);
  };
};

// ---------------------------------------------------------------- MedTechResolve
/** Out on the water: a swimmer drifts in and gets into trouble, waving. A
 *  small rescue boat with nobody aboard (a sensor mast, a launcher) comes in
 *  on its own, fires a life ring on a line; the swimmer grabs it, is reeled
 *  in and climbs up the low stern platform, and the boat carries them off. */
export const rescuePlay: Play = (svg, PW) => {
  const { room, defs } = stage(svg, PW);
  const SURF = 300;
  const clipId = 'above' + Math.random().toString(36).slice(2, 8);
  const cp = el('clipPath', { id: clipId }, defs);
  const clipPath = el('path', {}, cp);
  const above = el('g', { 'clip-path': `url(#${clipId})` }, room);
  const swim = el('g', {}, above);
  const swHead = el('circle', { r: 10, stroke: 'none' }, swim);
  const swArm1 = el('path', { fill: 'none', 'stroke-width': 6.5 }, swim);
  const swArm2 = el('path', { fill: 'none', 'stroke-width': 6.5 }, swim);
  const swBody = el('path', { stroke: 'none' }, swim);
  const boat = el('g', {}, above);
  el('path', { d: 'M -72 0 L 50 0 Q 74 -2 90 -24 L -60 -24 L -72 -12 Z', stroke: 'none' }, boat);             // hull, low stern step at the back
  el('rect', { x: -84, y: -14, width: 16, height: 5, stroke: 'none' }, boat);                                  // stern platform
  el('rect', { x: -30, y: -40, width: 40, height: 16, rx: 3, stroke: 'none' }, boat);                          // a covered console, no one at it
  el('path', { d: 'M -10 -40 L -10 -74 M -22 -74 L 2 -74 M -10 -74 L -10 -82', fill: 'none', 'stroke-width': 3 }, boat);   // sensor mast
  el('circle', { cx: -10, cy: -84, r: 4.5, stroke: 'none' }, boat);
  el('rect', { x: -26, y: -78, width: 8, height: 6, rx: 1, stroke: 'none' }, boat);
  el('path', { d: 'M -60 -24 L -60 -34 L 70 -34 L 86 -24', fill: 'none', 'stroke-width': 2.2 }, boat);
  const launcher = el('path', { fill: 'none', 'stroke-width': 6 }, boat);
  const ring = el('circle', { r: 10, fill: 'none', 'stroke-width': 5 }, room);
  const line = el('path', { fill: 'none', 'stroke-width': 1.4 }, room);
  const rider = el('g', {}, boat);
  el('circle', { cx: -50, cy: -54, r: 9.5, stroke: 'none' }, rider);
  el('path', { d: 'M -62 -26 Q -60 -48 -50 -46 Q -38 -46 -38 -26 Z', stroke: 'none' }, rider);
  el('circle', { cx: -50, cy: -36, r: 11, fill: 'none', 'stroke-width': 4.5 }, rider);                         // still holding the ring
  const wave = el('path', { fill: 'none', 'stroke-width': 4 }, room);
  const crests = el('path', { fill: 'none', 'stroke-width': 2 }, room);
  const LOOP = 14;
  const surf = (x: number, t: number) => SURF + Math.sin(x * 0.045 + t * 1.6) * 4 + Math.sin(x * 0.11 - t * 2.3) * 2;
  return (time: number) => {
    const t = time % LOOP;
    let d = '', c = `M -40 -100 L -40 ${surf(-40, t)}`;
    for (let x = -40; x <= 340; x += 10) { d += `${x === -40 ? 'M' : 'L'} ${x} ${surf(x, t)} `; c += ` L ${x} ${surf(x, t)}`; }
    set(wave, d); set(clipPath, c + ' L 340 -100 Z');
    let cr = '';
    for (let k = 0; k < 6; k++) { const x = ((k * 61 + t * 14) % 360) - 30; cr += `M ${x} ${surf(x, t) + 14 + (k % 2) * 16} q 6 -4 12 0 `; }
    set(crests, cr);
    // the boat: comes in 1.6..5, holds, leaves 10.4..13.6
    const bx = lerp(lerp(-160, 92, seg(t, 1.6, 5.0)), 480, seg(t, 10.4, 13.6));
    const by = surf(bx, t) + 6, roll = Math.sin(t * 1.9) * 2.5;
    boat.setAttribute('transform', `translate(${bx} ${by}) rotate(${roll})`);
    // the launcher on the bow swings up and fires at 5.6
    const aim = seg(t, 5.0, 5.5) * (1 - seg(t, 6.2, 6.8));
    set(launcher, `M 40 -30 L ${40 + Math.cos(-0.3 - aim * 0.6) * 18} ${-30 + Math.sin(-0.3 - aim * 0.6) * 18}`);
    // the swimmer, out at 228, struggling until the ring lands
    const sx0 = lerp(330, 228, seg(t, 0, 2.0));
    const reel = seg(t, 7.4, 9.0);                         // pulled in to the stern
    const climb = seg(t, 9.0, 9.8);
    const sternX = bx - 82, sternY = by - 14;
    const sx = lerp(sx0, sternX, reel), syBase = surf(sx, t) - 8 + Math.sin(t * 3.2) * 4 * (1 - reel);
    const grabbed = t > 6.9;
    const sy = lerp(syBase, sternY - 20, climb);
    const swimOn = t < 9.8;
    swim.setAttribute('opacity', swimOn ? '1' : '0');
    swHead.setAttribute('cx', String(sx)); swHead.setAttribute('cy', String(sy - 4 + Math.sin(t * 4.1) * 2 * (grabbed ? 0.3 : 1)));
    const fl = grabbed ? 0.15 : 1, a1 = Math.sin(t * 5.3) * 0.9 * fl, a2 = Math.sin(t * 4.4 + 1.3) * 0.9 * fl;
    if (grabbed) {     // both arms forward over the ring
      set(swArm1, `M ${sx - 6} ${sy + 8} L ${sx - 16} ${sy + 6} L ${sx - 22} ${sy + 4}`); set(swArm2, `M ${sx + 6} ${sy + 8} L ${sx - 6} ${sy + 4} L ${sx - 16} ${sy + 2}`);
    } else {
      set(swArm1, `M ${sx - 6} ${sy + 8} L ${sx - 16 + Math.sin(a1) * 10} ${sy - 20 - Math.cos(a1) * 8} L ${sx - 20 + Math.sin(a1) * 18} ${sy - 38}`);
      set(swArm2, `M ${sx + 6} ${sy + 8} L ${sx + 16 + Math.sin(a2) * 10} ${sy - 18 - Math.cos(a2) * 8} L ${sx + 18 + Math.sin(a2) * 16} ${sy - 36}`);
    }
    set(swBody, `M ${sx - 10} ${sy + 4} Q ${sx} ${sy - 4} ${sx + 10} ${sy + 4} L ${sx + 9} ${sy + 30} L ${sx - 9} ${sy + 30} Z`);
    // the ring: in its launcher, flying out in an arc, floating by the swimmer, held, then aboard
    const bow = { x: bx + 54, y: by - 42 };
    const fly = seg(t, 5.6, 6.6);
    let rx: number, ry: number;
    const landX = sx0 - 16, landY = surf(landX, t) - 2;
    if (t < 5.6) { rx = bow.x; ry = bow.y; }
    else if (t < 6.6) { rx = lerp(bow.x, landX, fly); ry = lerp(bow.y, landY, fly) - Math.sin(fly * Math.PI) * 70; }
    else if (t < 6.9) { rx = landX; ry = landY; }
    else { rx = sx - 18; ry = sy + 8; }
    const ringOn = t < 9.8 && t > 1.6;
    ring.setAttribute('cx', String(rx)); ring.setAttribute('cy', String(ry)); ring.setAttribute('opacity', ringOn ? '1' : '0');
    // its line, from the launcher, slack in flight, taut while reeling
    const sag = t < 7.4 ? 26 : 6;
    set(line, ringOn && t > 5.6 ? `M ${bow.x} ${bow.y} Q ${(bow.x + rx) / 2} ${(bow.y + ry) / 2 + sag} ${rx} ${ry}` : '');
    rider.setAttribute('opacity', String(t > 9.8 ? 1 : 0));
  };
};

// ---------------------------------------------------------------- Waterloo Reality Labs
/** Someone in a headset, reaching into a world only they can see: they
 *  pinch something out of the air, turn it in both hands, push it away,
 *  swipe past it, and reach for the next. All smooth loops, no cuts. */
export const vrPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  const who = person(room, { headset: true, hair: 'short', build: 1.05 });
  // key poses (front hand, back hand, look, lean) cycled with smooth blends
  const keys: { f: [number, number]; b: [number, number]; look: number; lean: number; x: number }[] = [
    { f: [166, 214], b: [150, 226], look: 0.05, lean: 3, x: 98 },      // reach out
    { f: [176, 186], b: [158, 196], look: 0.25, lean: 4, x: 100 },     // pinch something up high
    { f: [146, 206], b: [130, 208], look: 0.05, lean: 1, x: 96 },      // bring it in, both hands
    { f: [152, 218], b: [124, 196], look: -0.05, lean: 1, x: 96 },     // turn it
    { f: [186, 204], b: [136, 230], look: 0.1, lean: 6, x: 104 },      // push it away
    { f: [126, 196], b: [114, 250], look: 0.0, lean: 2, x: 100 },      // swipe across
    { f: [138, 262], b: [102, 284], look: -0.15, lean: 0, x: 98 },     // rest
  ];
  const DUR = 1.4, LOOP = keys.length * DUR;
  const mix = (a: number, b: number, s: number) => a + (b - a) * s;
  return (time: number) => {
    const t = time % LOOP;
    const i = Math.floor(t / DUR), s = ease((t - i * DUR) / DUR);
    const A = keys[i], B = keys[(i + 1) % keys.length];
    const wob = Math.sin(time * 1.3) * 2;
    const pinch = Math.max(0, Math.sin(time * 2.7)) * 3;
    who({
      x: mix(A.x, B.x, s) + Math.sin(time * 0.6) * 2, face: 1, walk: 0, ph: 0,
      lean: mix(A.lean, B.lean, s), look: mix(A.look, B.look, s) + Math.sin(time * 0.8) * 0.04,
      hand: [mix(A.f[0], B.f[0], s) + wob, mix(A.f[1], B.f[1], s) - pinch],
      hand2: [mix(A.b[0], B.b[0], s) - wob, mix(A.b[1], B.b[1], s) + pinch * 0.5],
    });
  };
};


// ---------------------------------------------------------------- the first three
/** A pine: trunk and five drooping tiers with ragged undersides. */
const pine = (x: number, base: number, h: number, sway: number) => {
  let d = `M ${x - 2.5} ${base} L ${x - 2} ${base - h * 0.2} L ${x + 2} ${base - h * 0.2} L ${x + 2.5} ${base} Z `;
  for (let k = 0; k < 5; k++) {
    const f = k / 5, y0 = base - h * (0.16 + f * 0.7), w = h * 0.34 * (1 - f * 0.78), tip = y0 - h * 0.26, sx = sway * (f + 0.2);
    d += `M ${x + sx * 0.6} ${tip} Q ${x + w * 0.5 + sx} ${y0 - h * 0.08} ${x + w + sx} ${y0 + 3}
      L ${x + w * 0.66 + sx} ${y0} L ${x + w * 0.45 + sx} ${y0 + 4} L ${x + w * 0.2 + sx} ${y0 + 1} L ${x + sx * 0.6} ${y0 + 5}
      L ${x - w * 0.2 + sx} ${y0 + 1} L ${x - w * 0.45 + sx} ${y0 + 4} L ${x - w * 0.66 + sx} ${y0} L ${x - w + sx} ${y0 + 3}
      Q ${x - w * 0.5 + sx} ${y0 - h * 0.08} ${x + sx * 0.6} ${tip} Z `;
  }
  return d;
};
/** A broadleaf tree: a forked trunk under a lumpy crown of overlapping lobes. */
const oak = (x: number, base: number, h: number, sway: number, seed: number) => {
  const r = rng0(seed);
  // trunk, then two limbs reaching up into the crown
  let d = `M ${x - 3.5} ${base} Q ${x - 2.5} ${base - h * 0.3} ${x - 2 + sway * 0.2} ${base - h * 0.46} L ${x + 2 + sway * 0.2} ${base - h * 0.46} Q ${x + 2.5} ${base - h * 0.3} ${x + 3.5} ${base} Z `;
  d += `M ${x - 1 + sway * 0.2} ${base - h * 0.44} L ${x - h * 0.16 + sway * 0.5} ${base - h * 0.62} L ${x - h * 0.14 + sway * 0.5} ${base - h * 0.64} L ${x + 1 + sway * 0.2} ${base - h * 0.47} Z `;
  d += `M ${x + 1 + sway * 0.2} ${base - h * 0.44} L ${x + h * 0.15 + sway * 0.5} ${base - h * 0.66} L ${x + h * 0.17 + sway * 0.5} ${base - h * 0.64} L ${x + 2 + sway * 0.2} ${base - h * 0.42} Z `;
  // a domed crown of small lobes: wide underneath, rounding over the top
  const lobes: [number, number, number][] = [];
  for (let k = 0; k <= 8; k++) { const a = Math.PI * (k / 8); lobes.push([Math.cos(a) * h * 0.27, -Math.sin(a) * h * 0.24, h * (0.09 + r() * 0.04)]); }
  for (let k = 0; k < 5; k++) lobes.push([(k - 2) * h * 0.11, h * 0.04 + (k % 2) * h * 0.02, h * (0.08 + r() * 0.03)]);
  for (let k = 0; k < 4; k++) lobes.push([(r() - 0.5) * h * 0.3, -h * (0.05 + r() * 0.12), h * 0.12]);
  const ox = x + sway, oy = base - h * 0.7;
  for (const [dx, dy, rr] of lobes) d += `M ${ox + dx - rr} ${oy + dy} a ${rr} ${rr} 0 1 0 ${rr * 2} 0 a ${rr} ${rr} 0 1 0 ${-rr * 2} 0 Z `;
  return d;
};
function rng0(seed: number) { let s0 = seed >>> 0; return () => { s0 = (s0 * 1664525 + 1013904223) >>> 0; return s0 / 4294967296; }; }

/** Forest loss: a wooded hillside swaying in the wind. A patch of it is
 *  felled, tree by tree, each one toppling; a satellite crosses high up, its
 *  scan sweeps the slope and corner brackets close in on the clearing; then
 *  saplings come up and grow back into the gap. */
export const forestPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  const hill = el('path', { stroke: 'none' }, room);
  hill.setAttribute('d', 'M -20 400 L -20 336 Q 60 316 150 326 Q 240 336 320 318 L 320 400 Z');
  const ground = (x: number) => 336 - 18 * Math.sin(((x + 20) / 340) * Math.PI) * 0.6 - (x > 150 ? (x - 150) * 0.05 : 0);
  const r = rng0(5);
  const trees = Array.from({ length: 15 }, (_, k) => {
    const x = -8 + k * 22 + (r() - 0.5) * 8, h = 70 + r() * 56, kind = r() < 0.6 ? 'pine' : 'oak';
    return { x, h, kind, seed: k * 31 + 7, g: el('path', { stroke: 'none' }, room), cut: k >= 6 && k <= 9, order: k - 6, ph: r() * 6 };
  });
  const sat = el('g', {}, room);
  el('rect', { x: -5, y: -4, width: 10, height: 8, rx: 1, stroke: 'none' }, sat);
  el('rect', { x: -24, y: -2.5, width: 16, height: 5, stroke: 'none' }, sat);
  el('rect', { x: 8, y: -2.5, width: 16, height: 5, stroke: 'none' }, sat);
  const beam = el('path', { stroke: 'none', opacity: 0 }, room);
  const marks = el('path', { fill: 'none', 'stroke-width': 3.2, opacity: 0 }, room);
  const LOOP = 15;
  return (time: number) => {
    const t = time % LOOP;
    for (const tr of trees) {
      const base = ground(tr.x) + 3;
      const sway = Math.sin(time * 1.3 + tr.ph) * 2.5;
      let fall = 0, grow = 1;
      if (tr.cut) { fall = seg(t, 1.0 + tr.order * 0.6, 1.9 + tr.order * 0.6); grow = seg(t, 9.6 + tr.order * 0.35, 13.8 + tr.order * 0.2); }
      const down = fall >= 1 && grow <= 0;
      const h = fall < 1 ? tr.h : Math.max(4, tr.h * grow);
      tr.g.setAttribute('d', down ? '' : tr.kind === 'pine' ? pine(tr.x, base, h, sway) : oak(tr.x, base, h, sway, tr.seed));
      // falling: tips over from its base, slowly then fast, and is gone
      const ang = fall < 1 ? Math.pow(fall, 2.2) * 86 * (tr.order % 2 ? -1 : 1) : 0;
      tr.g.setAttribute('transform', `rotate(${ang} ${tr.x} ${base})`);
      tr.g.setAttribute('opacity', String(fall < 1 ? 1 - Math.max(0, fall - 0.85) * 6.6 : 1));
    }
    // the satellite crosses 4..8.5, its scan sweeping down the slope as it passes
    const sp = seg(t, 4.0, 8.5);
    const sx = lerp(-40, 340, sp), sy = 44 + Math.sin(sp * Math.PI) * -10;
    sat.setAttribute('transform', `translate(${sx} ${sy})`);
    sat.setAttribute('opacity', String(t > 3.9 && t < 8.6 ? 1 : 0));
    const scan = seg(t, 5.0, 7.0) * (1 - seg(t, 7.2, 7.8));
    set(beam, `M ${sx - 3} ${sy + 4} L ${sx + 3} ${sy + 4} L ${sx + 40} 340 L ${sx - 40} 340 Z`);
    beam.setAttribute('opacity', String(scan * 0.22));
    // brackets close in on the clearing and blink
    const lock = seg(t, 6.4, 7.4) * (1 - seg(t, 10.6, 11.4));
    const gx0 = 112, gx1 = 218, gy0 = 228, gy1 = 340, pad = (1 - lock) * 36, L = 16;
    const X0 = gx0 - pad, X1 = gx1 + pad, Y0 = gy0 - pad, Y1 = gy1 + pad * 0.3;
    set(marks, `M ${X0} ${Y0 + L} L ${X0} ${Y0} L ${X0 + L} ${Y0} M ${X1 - L} ${Y0} L ${X1} ${Y0} L ${X1} ${Y0 + L}
      M ${X0} ${Y1 - L} L ${X0} ${Y1} L ${X0 + L} ${Y1} M ${X1 - L} ${Y1} L ${X1} ${Y1} L ${X1} ${Y1 - L}`);
    marks.setAttribute('opacity', String(lock * (t > 7.4 && t < 9 ? 0.6 + 0.4 * Math.round((Math.sin(t * 10) + 1) / 2) : 1)));
  };
};

/** The physics engine: a swarm of small balls that flows from one shape to
 *  the next (a turning sphere drawn in points and threads, counter-spinning
 *  rings, a two-armed spiral, a knotted loop), each ball chasing its place on
 *  a spring so the swarm lags, swirls and settles like something with mass. */
export const physicsPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  const N = 96, CX = 150, CY = 205;
  const balls = Array.from({ length: N }, (_, i) => ({ x: CX + Math.cos(i) * 60, y: CY + Math.sin(i) * 60, vx: 0, vy: 0, z: 0, g: el('circle', { stroke: 'none' }, room) }));
  const web = el('path', { fill: 'none', 'stroke-width': 1 }, room);
  const GA = Math.PI * (3 - Math.sqrt(5));
  const rotY = (x: number, y: number, z: number, a: number, tilt: number): [number, number, number] => {
    const X = x * Math.cos(a) + z * Math.sin(a), Z = -x * Math.sin(a) + z * Math.cos(a);
    return [X, y * Math.cos(tilt) - Z * Math.sin(tilt), y * Math.sin(tilt) + Z * Math.cos(tilt)];
  };
  const shapes: ((i: number, t: number) => [number, number, number])[] = [
    (i, t) => { const y = 1 - (2 * (i + 0.5)) / N, r = Math.sqrt(1 - y * y), a = i * GA; return rotY(Math.cos(a) * r * 95, y * 95, Math.sin(a) * r * 95, t * 0.6, 0.35); },
    (i, t) => { const ring = i % 3, k = Math.floor(i / 3), n = N / 3, R = [40, 72, 104][ring], dir = ring % 2 ? -1 : 1, a = (k / n) * Math.PI * 2 + dir * t * (0.9 - ring * 0.2); return rotY(Math.cos(a) * R, 0, Math.sin(a) * R, 0, 1.15 + ring * 0.05); },
    (i, t) => { const arm = i % 2, k = Math.floor(i / 2) / (N / 2), a = k * 5.2 + arm * Math.PI + t * 0.5, R = 12 + k * 110; return [Math.cos(a) * R, Math.sin(a) * R * 0.75, 0]; },
    (i, t) => { const u = (i / N) * Math.PI * 2 + t * 0.4; const x = Math.sin(u) + 2 * Math.sin(2 * u), y = Math.cos(u) - 2 * Math.cos(2 * u), z = -Math.sin(3 * u); return rotY(x * 32, y * 32, z * 32, t * 0.5, 0.3); },
  ];
  const HOLD = 4.2, LOOP = HOLD * shapes.length;
  let last = -1, first = true;
  return (time: number) => {
    const dt = last < 0 ? 0.016 : Math.min(0.05, Math.max(0, time - last)); last = time;
    const snap = first; first = false;
    const t = time % LOOP, idx = Math.floor(t / HOLD), f = seg(t - idx * HOLD, HOLD - 1.2, HOLD);
    const A = shapes[idx], B = shapes[(idx + 1) % shapes.length];
    for (let i = 0; i < N; i++) {
      const a = A(i, time), b = B(i, time);
      const tx = CX + lerp(a[0], b[0], f), ty = CY + lerp(a[1], b[1], f), tz = lerp(a[2], b[2], f);
      const p = balls[i];
      if (snap) { p.x = tx; p.y = ty; }
      // a spring with a little give: the swarm trails and overshoots, then settles
      const k = 26, damp = 6.5;
      p.vx += ((tx - p.x) * k - p.vx * damp) * dt; p.vy += ((ty - p.y) * k - p.vy * damp) * dt;
      p.x += p.vx * dt; p.y += p.vy * dt; p.z = tz;
      const r = 2.2 + (tz + 100) / 200 * 2.6;
      p.g.setAttribute('cx', String(p.x)); p.g.setAttribute('cy', String(p.y)); p.g.setAttribute('r', String(Math.max(1.2, r)));
    }
    // threads between near neighbours: the wireframe the swarm is drawing
    let d = '';
    for (let i = 0; i < N; i++) for (const j of [i + 1, i + 8, i + 13]) {
      if (j >= N) continue;
      const p = balls[i], q = balls[j], dx = p.x - q.x, dy = p.y - q.y;
      if (dx * dx + dy * dy < 34 * 34) d += `M ${p.x.toFixed(1)} ${p.y.toFixed(1)} L ${q.x.toFixed(1)} ${q.y.toFixed(1)} `;
    }
    set(web, d);
  };
};

/** Signwise: a hand spelling out letters of the ASL alphabet, up in the top
 *  left pane, clear of the window's cross bars. Every finger is three
 *  jointed segments rooted on the palm, so a curl folds it down over the
 *  palm like a real finger instead of leaving it dangling. */
export const signPlay: Play = (svg, PW) => {
  const { room, sx } = stage(svg, PW);
  const hand = el('g', {}, room);
  const arm = el('path', { stroke: 'none' }, hand);
  const palm = el('path', { stroke: 'none' }, hand);
  const fingers = [0, 1, 2, 3].map((k) => el('path', { fill: 'none', 'stroke-width': k === 3 ? 9.5 : 11 }, hand));
  const thumb = el('path', { fill: 'none', 'stroke-width': 12.5 }, hand);
  // per letter: curl of index, middle, ring, pinky (0 straight .. 1 folded), spread, thumb out (0 tucked .. 1 out), thumb across palm
  const L: Record<string, number[]> = {
    A: [1, 1, 1, 1, 0, 0.35, 0], B: [0, 0, 0, 0, 0, 0, 1], C: [0.45, 0.45, 0.45, 0.45, 0.05, 0.6, 0], L: [0, 1, 1, 1, 0, 1, 0],
    V: [0, 0, 1, 1, 0.45, 0, 1], Y: [1, 1, 1, 0, 0.2, 1, 0], I: [1, 1, 1, 0, 0, 0, 1], W: [0, 0, 0, 1, 0.35, 0, 1], O: [0.6, 0.62, 0.62, 0.6, 0, 0.45, 0.6],
  };
  const word = ['L', 'A', 'I', 'A', 'O', 'B', 'V', 'Y', 'W', 'C'];
  const DUR = 1.4;
  const cx = 74, cy = 122, S = 1.0;                       // in the top-left pane, clear of the cross bars
  const roots = [[-19, -30], [-6, -33], [7, -32], [18, -27]];
  const seglen = [[31, 20, 16], [35, 22, 17], [33, 21, 16], [25, 16, 13]];
  return (time: number) => {
    const n = word.length, tt = time % (n * DUR), i = Math.floor(tt / DUR);
    const s_ = ease(Math.min(1, ((tt - i * DUR) / DUR) * 1.7));
    const A = L[word[i]], B = L[word[(i + 1) % n]];
    const v = A.map((a, k) => a + (B[k] - a) * s_);
    const sway = Math.sin(time * 0.9) * 2, tilt = Math.sin(time * 0.6) * 0.05;
    // the stage stretches the room sideways to fit the glass: undo that for the hand
    hand.setAttribute('transform', `translate(${cx} ${cy}) scale(${S / sx} ${S}) rotate(${tilt * 57} 0 60) translate(${-cx} ${-cy})`);
    set(arm, `M ${cx - 16} ${cy + 32} Q ${cx - 17} ${cy + 120} ${cx - 23} ${cy + 300} L ${cx + 23} ${cy + 300} Q ${cx + 15} ${cy + 120} ${cx + 16} ${cy + 32} Z`);
    set(palm, `M ${cx - 25 + sway} ${cy - 32} Q ${cx + sway} ${cy - 40} ${cx + 24 + sway} ${cy - 28} Q ${cx + 27} ${cy + 4} ${cx + 21} ${cy + 30}
      Q ${cx} ${cy + 42} ${cx - 21} ${cy + 30} Q ${cx - 30} ${cy + 10} ${cx - 25 + sway} ${cy - 32} Z`);
    fingers.forEach((f, k) => {
      const curl = v[k];
      const spread = (k - 1.5) * v[4] * 0.22;
      // knuckle, middle and end joints bend together: projected onto the
      // glass a bent segment gets shorter, and past 90 degrees heads back down
      const ang = [curl * 1.55, curl * 1.75, curl * 1.2];
      let x = cx + roots[k][0] + sway, y = cy + roots[k][1], acc = 0, d = `M ${x} ${y + 4}`;
      for (let j = 0; j < 3; j++) {
        acc += ang[j];
        const l = seglen[k][j];
        x += Math.sin(spread) * l * Math.cos(acc) * 0.9; y -= l * Math.cos(acc);
        d += ` L ${x} ${y}`;
      }
      set(f, d);
    });
    // the thumb: from the heel of the palm, out to the side or across it
    const out = v[5], across = v[6];
    const t0 = [cx - 22 + sway, cy + 14];
    const a1 = -Math.PI / 2 - 0.9 * out + across * 0.9 - 0.15;
    const t1 = [t0[0] + Math.cos(a1) * 24, t0[1] + Math.sin(a1) * 24];
    const a2 = a1 + across * 1.1 + (1 - out) * 0.4;
    const t2 = [t1[0] + Math.cos(a2) * 18, t1[1] + Math.sin(a2) * 18];
    set(thumb, `M ${t0[0]} ${t0[1]} L ${t1[0]} ${t1[1]} L ${t2[0]} ${t2[1]}`);
  };
};

// ---------------------------------------------------------------- the sink-finding robot
/** Smoother than smoothstep: no jolt at either end. */
const glide = (t: number, a: number, b: number) => { const x = Math.min(1, Math.max(0, (t - a) / (b - a))); return x * x * x * (x * (6 * x - 15) + 10); };

/** A small robot rolls in, slows to a stop at the sink, swivels its camera
 *  up at the tap, raises a water-filter jug under it; the tap runs and you
 *  can see the jug fill, then it eases the jug down, turns round and rolls
 *  off. Every move eases in and out. */
export const robotPlay: Play = (svg, PW) => {
  const { room: outer } = stage(svg, PW);
  const room = el('g', { transform: 'translate(-46 0)' }, outer);    // the sink in the clear panes, off the right-hand bar
  el('rect', { x: 190, y: 250, width: 130, height: 12, stroke: 'none' }, room);            // counter top
  el('path', { d: 'M 200 262 L 200 396 M 300 262 L 300 396', fill: 'none', 'stroke-width': 8 }, room);   // cabinet sides
  el('path', { d: 'M 228 250 L 228 200 Q 228 188 240 188 L 258 188 Q 264 188 264 196 L 264 202', fill: 'none', 'stroke-width': 7 }, room); // tap
  el('rect', { x: 221, y: 212, width: 14, height: 6, rx: 2, stroke: 'none' }, room);
  const handle = el('path', { fill: 'none', 'stroke-width': 4 }, room);
  const stream = el('path', { fill: 'none', 'stroke-width': 3.2 }, room);
  const drops = [0, 1, 2].map(() => el('circle', { r: 1.6, stroke: 'none' }, room));
  const bot = el('g', {}, room);
  const body = el('g', {}, bot);
  el('rect', { x: -26, y: -40, width: 52, height: 34, rx: 6, stroke: 'none' }, body);
  const wheels = [-16, 16].map((wx) => { const w = el('g', {}, body); el('circle', { cx: 0, cy: 0, r: 9, stroke: 'none' }, w); w.dataset.x = String(wx); return w; });
  el('path', { d: 'M 0 -40 L 0 -64', fill: 'none', 'stroke-width': 4 }, body);
  const head = el('g', {}, body);
  el('rect', { x: -10, y: -7, width: 20, height: 13, rx: 3, stroke: 'none' }, head);
  el('circle', { cx: 9, cy: -1, r: 3, stroke: 'none' }, head);
  const arm = el('path', { fill: 'none', 'stroke-width': 5 }, body);
  // the jug: an outline you can see water through, so it visibly fills
  const jugWall = el('path', { fill: 'none', 'stroke-width': 3 }, room);
  const jugWater = el('path', { stroke: 'none', opacity: 0.7 }, room);
  const LOOP = 14;
  return (time: number) => {
    const t = time % LOOP;
    const arrive = glide(t, 0, 3.4), leave = glide(t, 10.4, 13.6);
    const x = lerp(lerp(-70, 196, arrive), -70, leave);
    const speed = (t < 3.4 || t > 10.4) ? Math.sin(Math.PI * Math.min(1, t < 3.4 ? t / 3.4 : (t - 10.4) / 3.2)) : 0;
    const turn = glide(t, 9.6, 10.4);                       // swivels round before leaving
    const face = Math.cos(turn * Math.PI);
    bot.setAttribute('transform', `translate(${x} ${392 - Math.abs(Math.sin(t * 9)) * 1.1 * speed})`);
    body.setAttribute('transform', `scale(${Math.sign(face) * Math.max(0.12, Math.abs(face))} 1)`);
    wheels.forEach((w) => w.setAttribute('transform', `translate(${w.dataset.x} -4) rotate(${(x * 4) % 360})`));
    const look = glide(t, 3.4, 4.0) * (1 - glide(t, 8.6, 9.2));
    head.setAttribute('transform', `translate(0 -70) rotate(${-look * 24})`);
    const up = glide(t, 4.0, 5.6) * (1 - glide(t, 8.0, 9.4));
    // where the jug's base is (arm's hand) in room units
    const ex = lerp(34, 58, up), ey = lerp(-30, -164, up);
    set(arm, `M 18 -30 Q ${lerp(40, 22, up)} ${lerp(-26, -96, up)} ${ex} ${ey}`);
    const jx = x + ex * Math.sign(face) * Math.max(0.12, Math.abs(face)), jy = 392 + ey;
    const JW = 26, JH = 34;
    const s_ = Math.sign(face) * Math.max(0.12, Math.abs(face));
    const L = jx - 4 * s_, R = jx + (JW - 4) * s_;
    set(jugWall, `M ${L} ${jy - JH} L ${L + 1 * s_} ${jy} L ${R - 1 * s_} ${jy} L ${R} ${jy - JH}
      M ${R} ${jy - JH + 6} q ${8 * s_} 2 ${6 * s_} 14 q ${-2 * s_} 6 ${-6 * s_} 6 M ${L - 2 * s_} ${jy - JH} L ${R + 2 * s_} ${jy - JH}`);
    // the tap: its handle turns, water runs straight down into the jug, the level rises
    const on = glide(t, 5.8, 6.1) * (1 - glide(t, 7.7, 8.0));
    set(handle, `M 228 214 l ${-8 * on} ${-10 + 4 * on}`);
    const fill = glide(t, 6.0, 7.9);
    const level = (fill * 0.75 + 0.08) * (t > 12.5 ? 1 - glide(t, 12.5, 13.8) : 1);    // the jug's emptied off-screen by the next visit
    const wy = jy - JH * level;
    set(jugWater, level > 0.02 ? `M ${L + 1.5 * s_} ${wy} L ${L + 2 * s_} ${jy - 1.5} L ${R - 2 * s_} ${jy - 1.5} L ${R - 1.5 * s_} ${wy} Z` : '');
    const top = 204;
    set(stream, on > 0.05 ? `M 264 ${top} L 264 ${Math.max(top, wy)}` : '');
    stream.setAttribute('opacity', String(on));
    stream.setAttribute('stroke-width', String(2 + 2.8 * on));
    drops.forEach((d, k) => {
      const ph = (time * 3 + k / 3) % 1;
      d.setAttribute('cx', String(264 + (k - 1) * 4 * ph)); d.setAttribute('cy', String(wy - 2 - Math.sin(ph * Math.PI) * 6));
      d.setAttribute('opacity', String(on * (1 - ph)));
    });
  };
};

// ---------------------------------------------------------------- desk scenes
function desk(room: Element) {
  el('rect', { x: 120, y: 290, width: 150, height: 10, stroke: 'none' }, room);             // desk top
  el('path', { d: 'M 130 300 L 130 396 M 260 300 L 260 396', fill: 'none', 'stroke-width': 8 }, room);
  el('path', { d: 'M 40 300 L 96 300 M 46 300 L 46 396 M 90 300 L 90 396 M 44 300 L 40 210', fill: 'none', 'stroke-width': 7 }, room); // chair
  const lid = el('path', { stroke: 'none' }, room);
  lid.setAttribute('d', 'M 150 290 L 196 290 L 205 246 L 202 244 Z');                     // laptop
}

/** Waterloo API + WatIf: someone at a laptop under a wall calendar; days get
 *  ticked off one by one, then the page is flipped up for a fresh month. */
export const calendarPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  desk(room);
  const who = person(room, { hair: 'long', build: 0.95 });
  const page = el('g', {}, room);
  el('rect', { x: 150, y: 60, width: 130, height: 110, rx: 3, fill: 'none', 'stroke-width': 4 }, page);
  el('rect', { x: 150, y: 60, width: 130, height: 18, stroke: 'none' }, page);
  const ticks: Element[] = [];
  for (let r = 0; r < 4; r++) for (let k = 0; k < 6; k++) {
    el('rect', { x: 158 + k * 20, y: 86 + r * 20, width: 14, height: 14, fill: 'none', 'stroke-width': 1.5 }, page);
    ticks.push(el('path', { d: `M ${160 + k * 20} ${93 + r * 20} l 4 5 l 8 -10`, fill: 'none', 'stroke-width': 3, opacity: 0 }, page));
  }
  const LOOP = 12;
  return (time: number) => {
    const t = time % LOOP;
    const typing = Math.sin(time * 14) * 2;
    const n = Math.floor(Math.min(9.2, t) / 0.95);
    ticks.forEach((k, i) => k.setAttribute('opacity', i < n ? '1' : '0'));
    const flip = seg(t, 10.2, 11.4);
    page.setAttribute('transform', `translate(0 ${-flip * 160}) `);
    page.setAttribute('opacity', String(1 - flip * 0.9 + seg(t, 11.5, 12) * 0.9));
    who({ x: 84, face: 1, walk: 0, ph: 0, sit: true, hipY: 296, lean: 6, look: t > 9 && t < 10.5 ? 0.35 : -0.1,
      hand: [164 + typing, 284], hand2: [154 - typing, 286] });
  };
};

/** SaaS: someone at a laptop builds a stack of blocks one at a time, then
 *  slides the finished stack off along the desk and starts again. */
export const blocksPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  desk(room);
  const who = person(room);
  const blocks = Array.from({ length: 5 }, () => el('rect', { width: 34, height: 18, rx: 2, stroke: 'none' }, room));
  const LOOP = 11;
  return (time: number) => {
    const t = time % LOOP;
    const typing = Math.sin(time * 14) * 2;
    const ship = seg(t, 8.8, 10.4);
    let reach: [number, number] | null = null;
    blocks.forEach((b, i) => {
      const t0 = 0.6 + i * 1.5;
      const land = seg(t, t0, t0 + 0.6);
      const bx = 222 + (i % 2) * 4 + ship * 120, by = 290 - 18 * (i + 1);
      const x = lerp(170, bx, land), y = lerp(250, by, land) - Math.sin(land * Math.PI) * 20;
      b.setAttribute('x', String(x)); b.setAttribute('y', String(y));
      b.setAttribute('opacity', String(t < t0 ? 0 : 1));
      if (t > t0 - 0.3 && t < t0 + 0.7) reach = [x + 6, y + 9];
    });
    const r = reach as [number, number] | null;
    who({ x: 84, face: 1, walk: 0, ph: 0, sit: true, hipY: 296, lean: 6, look: r ? 0.05 : -0.1,
      hand: r ?? [164 + typing, 284], hand2: [154 - typing, 286] });
  };
};

// ---------------------------------------------------------------- community
/** Someone turning in profile: squeeze to nothing and open out the other
 *  way (k from 1 to -1). The person is always drawn facing +1 inside. */
function turner(parent: Element, look: Look) {
  const g = el('g', {}, parent);
  const who = person(g, look);
  return (x: number, k: number, pose: Omit<Pose, 'x' | 'face'>) => {
    const kk = Math.sign(k || 1) * Math.max(0.2, Math.abs(k));
    const loc = (pt: [number, number]): [number, number] => [x + (pt[0] - x) / kk, pt[1]];
    g.setAttribute('transform', `translate(${x} 0) scale(${k} 1) translate(${-x} 0)`);
    const r = who({ ...pose, x, face: 1, hand: loc(pose.hand), hand2: loc(pose.hand2) });
    const back = (pt: [number, number]): [number, number] => [x + (pt[0] - x) * k, pt[1]];
    return { ...r, hand: back(r.hand), hand2: back(r.hand2) };
  };
}

/** A soup kitchen counter. The cook ladles soup from a steaming pot into a
 *  bowl, turns, and holds it out across the counter; the guest takes it in
 *  both hands, nods their thanks and walks off carrying it, still steaming.
 *  The cook goes back to stirring; the next guest, someone else, comes in.
 *  Everything happens in the clear panes between the window's bars. */
export const servePlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  el('rect', { x: 140, y: 300, width: 190, height: 10, rx: 2, stroke: 'none' }, room);       // counter top
  el('rect', { x: 150, y: 310, width: 170, height: 90, stroke: 'none' }, room);
  const POT = { x: 270, w: 46, top: 262 };
  const pot = el('path', { stroke: 'none' }, room);
  pot.setAttribute('d', `M ${POT.x} 300 L ${POT.x + 2} ${POT.top} L ${POT.x + POT.w - 2} ${POT.top} L ${POT.x + POT.w} 300 Z
    M ${POT.x - 4} ${POT.top} L ${POT.x + POT.w + 4} ${POT.top} L ${POT.x + POT.w + 4} ${POT.top - 5} L ${POT.x - 4} ${POT.top - 5} Z
    M ${POT.x - 8} ${POT.top + 8} l 8 0 l 0 5 l -8 0 Z M ${POT.x + POT.w} ${POT.top + 8} l 8 0 l 0 5 l -8 0 Z`);
  const potSteam = [0, 1, 2, 3].map(() => el('path', { fill: 'none', 'stroke-width': 3.2 }, room));
  const cook = turner(room, { hair: 'cap', apron: true, build: 1.14, height: 1.02 });
  const guests = [turner(room, { hair: 'curly', build: 1.06, height: 0.95 }), turner(room, { hair: 'long', height: 1.04, build: 0.94 })];
  const guestG = [...room.children].slice(-2) as SVGGElement[];
  const ladle = el('path', { fill: 'none', 'stroke-width': 3 }, room);
  const bowl = el('path', { stroke: 'none' }, room);
  const bowlSteam = [0, 1, 2].map(() => el('path', { fill: 'none', 'stroke-width': 2.6 }, room));
  const LOOP = 13;
  const bowlAt = (x: number, y: number) => `M ${x - 21} ${y - 10} L ${x + 21} ${y - 10} Q ${x + 19} ${y + 7} ${x + 6} ${y + 9} L ${x + 7} ${y + 13} L ${x - 7} ${y + 13} L ${x - 6} ${y + 9} Q ${x - 19} ${y + 7} ${x - 21} ${y - 10} Z
    M ${x - 24} ${y - 12} L ${x + 24} ${y - 12} L ${x + 24} ${y - 9} L ${x - 24} ${y - 9} Z`;
  const wisp = (e: Element, x: number, y: number, ph: number, h: number, time: number, k: number) => {
    const sw = Math.sin(time * 1.7 + ph * 5) * 4;
    set(e, `M ${x} ${y} q ${5 + sw} ${-h * 0.25} ${sw * 0.6} ${-h * 0.5} q ${-5 + sw * 0.3} ${-h * 0.25} ${sw + 3} ${-h * 0.5}`);
    e.setAttribute('opacity', String(Math.sin(ph * Math.PI) * 0.75 * k));
  };
  return (time: number) => {
    const t = time % LOOP, which = Math.floor(time / LOOP) % 2;
    guestG.forEach((g, i) => g.setAttribute('opacity', i === which ? '1' : '0'));
    // the pot steams the whole time, drifting right, away from the cook
    potSteam.forEach((e, k) => { const ph = (time * 0.42 + k / 4) % 1; wisp(e, POT.x + 12 + k * 7 + ph * 14, POT.top - 8 - ph * 70, ph, 34, time, 1); });
    // ---- the cook (stands at 250)
    const cx = 250;
    const turnA = seg(t, 2.2, 2.6), turnB = seg(t, 9.0, 9.4);
    const k = 1 - 2 * turnA + 2 * turnB;                       // +1 facing the pot, -1 facing the guest
    const dip = seg(t, 0.3, 0.9) * (1 - seg(t, 1.1, 1.5)), pour = seg(t, 1.2, 1.6) * (1 - seg(t, 1.8, 2.1));
    const reach = seg(t, 2.7, 3.6) * (1 - seg(t, 4.2, 4.9));    // holding the bowl out
    const stir = seg(t, 9.5, 10.0);
    const filled = t > 1.7;
    // the bowl: in the cook's back hand, then both hands, then across, then the guest's
    const gx = lerp(lerp(-60, 104, seg(t, 0, 2.4)), -70, seg(t, 5.8, 8.6));
    const gk = 1 - 2 * seg(t, 5.3, 5.7);
    const take = seg(t, 4.1, 4.9);
    const handBowl: [number, number] = t < 2.2 ? [262, 236] : [lerp(lerp(226, 182, reach), 182, 0), lerp(216, 212, reach)];
    const guestHold: [number, number] = [gx + gk * 24, 224];
    const bxy: [number, number] = t < 4.1 ? handBowl : t < 5.3 ? [lerp(182, 130, take), lerp(212, 224, take)] : guestHold;
    const showBowl = t < 8.8;
    let cHand: [number, number], cHand2: [number, number];
    if (t < 2.2) {
      const lx = lerp(lerp(278, 290, dip), 270, pour), ly = lerp(lerp(246, 268, dip), 226, pour);
      cHand = [lx, ly]; cHand2 = [bxy[0] - 4, bxy[1] + 6];
      set(ladle, `M ${lx} ${ly} L ${lx + 8 - pour * 10} ${ly + 22 - pour * 16} m -5 0 a 5 4 0 1 0 10 0 Z`);
    } else if (t < 4.9) {
      cHand = [bxy[0] + 14, bxy[1] + 7]; cHand2 = [bxy[0] - 14, bxy[1] + 7];
      if (t > 4.1) { cHand = [lerp(cHand[0], 214, take), lerp(cHand[1], 296, take)]; cHand2 = [lerp(cHand2[0], 222, take), lerp(cHand2[1], 298, take)]; }
      set(ladle, '');
    } else if (t < 9.0) {
      const wave = seg(t, 5.0, 5.4) * (1 - seg(t, 6.0, 6.5));
      cHand = [214, 296]; cHand2 = [lerp(222, 214, wave), lerp(298, 196 + Math.sin(t * 12) * 4, wave)];
      set(ladle, '');
    } else {
      const a = t * 3.2;
      cHand = [lerp(262, 290 + Math.cos(a) * 7, stir), lerp(280, 258 + Math.sin(a) * 2, stir)]; cHand2 = [244, 292];
      set(ladle, stir > 0.5 ? `M ${cHand[0]} ${cHand[1]} L ${cHand[0] + 4} ${cHand[1] + 20}` : '');
    }
    if (t >= 12.4) { const r_ = seg(t, 12.4, 13); cHand = [lerp(cHand[0], 278, r_), lerp(cHand[1], 246, r_)]; }
    cook(cx, k, { walk: 0, ph: 0, lean: 4 + reach * 5, look: t < 2.2 ? -0.35 : t < 5.2 ? -0.1 : -0.2, hand: cHand, hand2: cHand2 });
    // ---- the guest
    const walking = t < 2.4 || t > 5.8;
    const nod = seg(t, 4.9, 5.1) * (1 - seg(t, 5.15, 5.35));
    const gHands: [[number, number], [number, number]] = t < 3.2 ? restHands(gx, gk, walking ? 1 : 0, t * 7.5) :
      t < 4.1 ? [[lerp(gx + 8, bxy[0] - 9, seg(t, 3.2, 3.9)), lerp(300, bxy[1] + 6, seg(t, 3.2, 3.9))], [lerp(gx - 4, bxy[0] - 14, seg(t, 3.2, 3.9)), lerp(298, bxy[1] + 8, seg(t, 3.2, 3.9))]]
      : [[bxy[0] + gk * 14, bxy[1] + 7], [bxy[0] - gk * 14, bxy[1] + 8]];
    guests[which](gx, gk, { walk: walking ? 1 : 0, ph: t * 7.5, lean: walking ? 0 : 2, look: 0.06 - nod * 0.35 - (t > 5.8 ? 0.15 : 0), hand: gHands[0], hand2: gHands[1] });
    set(bowl, showBowl ? bowlAt(bxy[0], bxy[1]) : '');
    bowlSteam.forEach((e, j) => { const ph = (time * 0.55 + j / 3) % 1; wisp(e, bxy[0] - 9 + j * 9, bxy[1] - 14 - ph * 40, ph, 24, time, filled && showBowl ? 0.9 : 0); });
  };
};

// ---------------------------------------------------------------- lilies
function lilies(room: Element, x0: number, n = 3) {
  const g = el('g', {}, room);
  el('path', { d: `M ${x0 - 34} 396 L ${x0 - 28} 352 L ${x0 + 28} 352 L ${x0 + 34} 396 Z`, stroke: 'none' }, g);   // pot
  for (let k = 0; k < n; k++) {
    const sx = x0 - 14 + k * 14, top = 190 + k * 26 + (k === 1 ? -30 : 0), lean = (k - 1) * 14;
    el('path', { d: `M ${sx} 352 Q ${sx + lean * 0.3} ${(352 + top) / 2} ${sx + lean} ${top}`, fill: 'none', 'stroke-width': 4 }, g);
    const fx = sx + lean, fy = top;
    el('path', { d: `M ${fx} ${fy} l -14 -30 q 4 6 9 4 z M ${fx} ${fy} l 14 -30 q -4 6 -9 4 z M ${fx} ${fy} l -4 -36 l 8 0 z M ${fx} ${fy} l -20 -18 l 4 -4 z M ${fx} ${fy} l 20 -18 l -4 -4 z`, stroke: 'none' }, g);
    el('path', { d: `M ${sx} 352 Q ${sx - 30 + k * 20} 320 ${sx - 40 + k * 34} 268`, fill: 'none', 'stroke-width': 6 }, g);   // strap leaves
  }
  return g;
}

/** Lily and Rain: the lilies stand still; once you pick this window it
 *  starts to rain, softly at first, streaks running down the glass. */
export const rainPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  lilies(room, 150);
  const drops = Array.from({ length: 46 }, (_, k) => ({ x: (k * 53) % 320 - 10, ph: (k * 0.37) % 1, sp: 1.1 + ((k * 13) % 7) / 10,
    g: el('path', { fill: 'none', 'stroke-width': 2 }, room) }));
  return (t: number) => {
    const amt = Math.min(1, t / 1.6);
    drops.forEach((d, k) => {
      const u = (t * d.sp + d.ph) % 1, y = -30 + u * 450, x = d.x + u * 40;
      const on = k / drops.length < amt ? 1 : 0;
      set(d.g, `M ${x} ${y} l 5 22`);
      d.g.setAttribute('opacity', String(on * 0.75));
    });
  };
};

/** Lily and Fire: the lilies stand still; pick this window and a flame
 *  catches with a flare, then burns and flickers behind them. */
export const firePlay: Play = (svg, PW) => {
  const st = stage(svg, PW);
  const glowId = 'glow' + Math.random().toString(36).slice(2, 8);
  const f = el('filter', { id: glowId, x: '-50%', y: '-50%', width: '200%', height: '200%' }, st.defs);
  el('feGaussianBlur', { stdDeviation: 5 }, f);
  const light = el('g', { transform: `scale(${st.sx} 1)`, filter: `url(#${glowId})` }, st.svg);
  st.svg.insertBefore(light, st.shadow);
  const flare = el('circle', { cx: 150, cy: 330, r: 10, fill: '#fff3d6', opacity: 0 }, light);
  const flames = [0, 1, 2, 3, 4].map((k) => el('path', { fill: k % 2 ? '#ffb45c' : '#ffd88a', opacity: 0 }, light));
  lilies(st.room, 150);
  return (t: number) => {
    const fl = Math.max(0, 1 - Math.abs(t - 0.25) / 0.35);
    flare.setAttribute('r', String(10 + fl * 90)); flare.setAttribute('opacity', String(fl));
    const burn = seg(t, 0.2, 1.2);
    flames.forEach((p, k) => {
      const x = 92 + k * 30, h = (150 + (k % 3) * 60) * burn * (0.82 + 0.18 * Math.sin(t * 9 + k * 2)), w = 20 + (k % 2) * 8;
      const sw = Math.sin(t * 5 + k) * 8;
      set(p, `M ${x - w} 380 Q ${x - w} ${380 - h * 0.5} ${x + sw} ${380 - h} Q ${x + w} ${380 - h * 0.5} ${x + w} 380 Z`);
      p.setAttribute('opacity', String(burn * 0.85));
    });
  };
};
