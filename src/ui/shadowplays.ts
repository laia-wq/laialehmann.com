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
  return { room, sx, defs, filter: `url(#${id})`, svg };
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
}

/** A person in profile: legs that bend at the knee and lift their feet,
 *  a jumper with a hem, arms with elbows and hands, a head with a brow,
 *  nose, lips and chin, hair in a bun (or a headset strapped on). */
export function person(parent: Element, opts: { headset?: boolean } = {}) {
  const g = el('g', {}, parent);
  const legBack = el('path', { fill: 'none', 'stroke-width': 13 }, g);
  const shoeBack = el('path', { stroke: 'none' }, g);
  const armBack = el('path', { fill: 'none', 'stroke-width': 9 }, g);
  const handBack = el('circle', { r: 5, stroke: 'none' }, g);
  const torso = el('path', { stroke: 'none' }, g);
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
  return (p: Pose) => {
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
    const lb = leg(-1), lf = leg(1);
    set(legBack, lb.d); set(shoeBack, lb.shoe); set(legFront, lf.d); set(shoeFront, lf.shoe);
    set(torso, `M ${X(-5 + lean)} ${shY - 8} Q ${X(-17 + lean)} ${shY - 4} ${X(-17 + lean)} ${shY + 10} Q ${X(-19)} ${shY + 50} ${X(-15)} ${hipY - 6}
      Q ${X(-17)} ${hipY + 4} ${X(-14)} ${hipY + 9} L ${X(15)} ${hipY + 9} Q ${X(18)} ${hipY + 2} ${X(15)} ${hipY - 8}
      Q ${X(13)} ${shY + 52} ${X(18 + lean)} ${shY + 22} Q ${X(19 + lean)} ${shY + 4} ${X(10 + lean)} ${shY - 2} L ${X(6 + lean)} ${shY - 10} Z`);
    const hx = X(4 + lean * 1.4), hy = shY - 30;
    const P = (u: number, v: number) => `${hx + face * u} ${hy + v}`;
    set(head, `M ${P(-12, -14)} Q ${P(-2, -22)} ${P(9, -16)} Q ${P(14, -10)} ${P(13, -3)} L ${P(18, 3)} Q ${P(19, 5)} ${P(14, 6)}
      Q ${P(15, 9)} ${P(13, 10)} Q ${P(14, 13)} ${P(11, 15)} Q ${P(9, 19)} ${P(3, 19)} Q ${P(-1, 19)} ${P(-1, 24)} L ${P(-1, 31)}
      L ${P(-9, 31)} Q ${P(-10, 22)} ${P(-14, 14)} Q ${P(-17, 0)} ${P(-12, -14)} Z`);
    set(hair, `M ${P(10, -12)} Q ${P(6, -24)} ${P(-6, -21)} Q ${P(-16, -18)} ${P(-17, -5)} Q ${P(-18, 4)} ${P(-14, 10)}
      Q ${P(-12, 2)} ${P(-11, -4)} Q ${P(-2, -14)} ${P(10, -12)} Z
      M ${P(-14, -14)} m ${-face * 5} 0 a 8 8 0 1 0 ${face * 0.1} 0 Z`);
    set(strands, `M ${P(-19, -12)} q ${-face * 5} 6 ${-face * 3} 12 M ${P(-16, -6)} q ${-face * 2} 7 ${-face * 1} 12`);
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
    return { shY, hipY, hand: [aF.ex, aF.ey] as [number, number], hand2: [aB.ex, aB.ey] as [number, number] };
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
  const { room, sx } = stage(svg, PW);
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
  const who = person(room);
  const phone = el('rect', { width: 7, height: 12, rx: 1.5, stroke: 'none' }, room);
  const glow = el('ellipse', { rx: 6, ry: 4.5, fill: '#fff1d2', stroke: 'none', opacity: 0 }, svg);
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
      const [r1, r2] = restHands(x, face, walk, ph);
      hand = [lerp(r1[0], x + face * 32, out), lerp(r1[1], shY + 30, out)];
      hand2 = [lerp(r2[0], x + face * 27, out), lerp(r2[1], shY + 35, out)];
    } else [hand, hand2] = restHands(x, face, walk, ph);
    const r = who({ x, face, walk, ph, lean: out * 4, look: -out * 0.25, hand, hand2 });
    const [hX, hY] = r.hand;
    phone.setAttribute('x', String(hX + face * 2 - 3.5)); phone.setAttribute('y', String(hY - 14));
    phone.setAttribute('opacity', String(Math.min(1, out * 1.5)));
    glow.setAttribute('cx', String((hX + face * 2) * sx)); glow.setAttribute('cy', String(hY - 8));
    glow.setAttribute('opacity', String(out * out * 0.7));
  };
};

// ---------------------------------------------------------------- WARG
/** Someone with a controller sets a drone humming: it lifts off, wobbles,
 *  climbs and drifts away (smaller and smaller) out of the top of the glass,
 *  then comes back down and lands where it started. */
export const dronePlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  const who = person(room);
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
/** Out on the water: a swimmer drifts in, gets into trouble and waves for
 *  help; a small rescue boat comes in from the left, someone leans over and
 *  hauls them aboard, and the boat heads off to the right. */
export const rescuePlay: Play = (svg, PW) => {
  const { room, defs } = stage(svg, PW);
  const SURF = 300;
  const clipId = 'above' + Math.random().toString(36).slice(2, 8);
  const cp = el('clipPath', { id: clipId }, defs);
  const clipPath = el('path', {}, cp);
  const above = el('g', { 'clip-path': `url(#${clipId})` }, room);
  // the swimmer: head and arms above the water
  const swHead = el('circle', { r: 11, stroke: 'none' }, above);
  const swArm1 = el('path', { fill: 'none', 'stroke-width': 7 }, above);
  const swArm2 = el('path', { fill: 'none', 'stroke-width': 7 }, above);
  const swBody = el('path', { stroke: 'none' }, above);
  // the boat: hull, a console with a windscreen, a rail, the rescuer
  const boat = el('g', {}, above);
  el('path', { d: 'M -70 0 L 58 0 Q 78 -2 92 -22 L -62 -22 Q -72 -14 -70 0 Z', stroke: 'none' }, boat);
  el('rect', { x: -36, y: -46, width: 26, height: 24, rx: 2, stroke: 'none' }, boat);
  el('path', { d: 'M -10 -46 L 0 -60 L 3 -58 L -6 -46 Z', stroke: 'none' }, boat);
  el('path', { d: 'M -64 -22 L -64 -34 L 70 -34 L 84 -24', fill: 'none', 'stroke-width': 2.5 }, boat);
  el('path', { d: 'M -68 -22 L -68 -60 M -68 -60 L -54 -54 L -68 -50', fill: 'none', 'stroke-width': 2 }, boat);   // pennant
  const ring = el('circle', { r: 9, fill: 'none', 'stroke-width': 5 }, boat);
  const rescuer = el('g', {}, boat);
  const rsBody = el('path', { stroke: 'none' }, rescuer);
  const rsHead = el('circle', { r: 10, stroke: 'none' }, rescuer);
  const rsArm = el('path', { fill: 'none', 'stroke-width': 7 }, rescuer);
  const hauled = el('g', {}, boat);
  const haHead = el('circle', { r: 10, stroke: 'none' }, hauled);
  const haBody = el('path', { stroke: 'none' }, hauled);
  const wave = el('path', { fill: 'none', 'stroke-width': 4 }, room);
  const crests = el('path', { fill: 'none', 'stroke-width': 2 }, room);
  const LOOP = 12;
  const surf = (x: number, t: number) => SURF + Math.sin(x * 0.045 + t * 1.6) * 4 + Math.sin(x * 0.11 - t * 2.3) * 2;
  return (time: number) => {
    const t = time % LOOP;
    // the water line, and everything below it hidden
    let d = '', c = `M -40 -100 L -40 ${surf(-40, t)}`;
    for (let x = -40; x <= 340; x += 10) { d += `${x === -40 ? 'M' : 'L'} ${x} ${surf(x, t)} `; c += ` L ${x} ${surf(x, t)}`; }
    set(wave, d); set(clipPath, c + ' L 340 -100 Z');
    let cr = '';
    for (let k = 0; k < 6; k++) { const x = ((k * 61 + t * 14) % 360) - 30; cr += `M ${x} ${surf(x, t) + 14 + (k % 2) * 16} q 6 -4 12 0 `; }
    set(crests, cr);
    // swimmer: drifts in from the right, struggles, is hauled out at 7s
    const sx0 = lerp(330, 214, seg(t, 0, 2.2));
    const inBoat = seg(t, 7.0, 7.8);
    const sy = surf(sx0, t) - 8 + Math.sin(t * 3.2) * 4;
    const flail = t < 7 ? 1 : 0;
    swHead.setAttribute('cx', String(sx0)); swHead.setAttribute('cy', String(sy - 4 + Math.sin(t * 4.1) * 2));
    swHead.setAttribute('opacity', String(1 - inBoat));
    const a1 = Math.sin(t * 5.3) * 0.9 * flail, a2 = Math.sin(t * 4.4 + 1.3) * 0.9 * flail;
    set(swArm1, `M ${sx0 - 6} ${sy + 8} L ${sx0 - 16 + Math.sin(a1) * 10} ${sy - 20 - Math.cos(a1) * 8} L ${sx0 - 20 + Math.sin(a1) * 18} ${sy - 38}`);
    set(swArm2, `M ${sx0 + 6} ${sy + 8} L ${sx0 + 16 + Math.sin(a2) * 10} ${sy - 18 - Math.cos(a2) * 8} L ${sx0 + 18 + Math.sin(a2) * 16} ${sy - 36}`);
    swArm1.setAttribute('opacity', String(1 - inBoat)); swArm2.setAttribute('opacity', String(1 - inBoat));
    set(swBody, `M ${sx0 - 10} ${sy + 4} Q ${sx0} ${sy - 4} ${sx0 + 10} ${sy + 4} L ${sx0 + 9} ${sy + 30} L ${sx0 - 9} ${sy + 30} Z`);
    swBody.setAttribute('opacity', String(1 - inBoat));
    // boat: comes in 2.2..5.6, waits, leaves 8.2..11.4
    const bx = lerp(lerp(-140, 128, seg(t, 2.2, 5.6)), 470, seg(t, 8.2, 11.4));
    const by = surf(bx, t) + 6;
    const roll = Math.sin(t * 1.9) * 2.5;
    boat.setAttribute('transform', `translate(${bx} ${by}) rotate(${roll})`);
    // the rescuer leans out over the bow and reaches down
    const lean = seg(t, 5.4, 6.4) * (1 - seg(t, 7.4, 8.0));
    set(rsBody, `M 18 -34 L 40 -34 L ${38 + lean * 10} ${-80 + lean * 18} L ${22 + lean * 8} ${-82 + lean * 18} Z`);
    rsHead.setAttribute('cx', String(32 + lean * 16)); rsHead.setAttribute('cy', String(-92 + lean * 22));
    const reachX = lerp(46, sx0 - bx + 8, lean), reachY = lerp(-60, sy - by - 18, lean);
    set(rsArm, `M ${36 + lean * 10} ${-72 + lean * 18} L ${(36 + reachX) / 2 + 6} ${(-72 + reachY) / 2} L ${reachX} ${reachY}`);
    ring.setAttribute('cx', String(-46)); ring.setAttribute('cy', String(-44));
    // the swimmer, now sitting in the boat wrapped up, from 7s until the loop ends
    hauled.setAttribute('opacity', String(inBoat));
    haHead.setAttribute('cx', '58'); haHead.setAttribute('cy', String(-60 + (1 - inBoat) * 30));
    set(haBody, 'M 46 -34 Q 50 -54 58 -52 Q 68 -52 70 -34 Z');
  };
};

// ---------------------------------------------------------------- Waterloo Reality Labs
/** Someone in a headset, reaching into a world only they can see: they
 *  pinch something out of the air, turn it in both hands, push it away,
 *  swipe past it, and reach for the next. All smooth loops, no cuts. */
export const vrPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  const who = person(room, { headset: true });
  // key poses (front hand, back hand, look, lean) cycled with smooth blends
  const keys: { f: [number, number]; b: [number, number]; look: number; lean: number; x: number }[] = [
    { f: [186, 214], b: [170, 226], look: 0.05, lean: 3, x: 128 },     // reach out
    { f: [196, 186], b: [178, 196], look: 0.25, lean: 4, x: 130 },     // pinch something up high
    { f: [170, 206], b: [154, 208], look: 0.05, lean: 1, x: 126 },     // bring it in, both hands
    { f: [176, 218], b: [146, 196], look: -0.05, lean: 1, x: 126 },    // turn it
    { f: [210, 204], b: [160, 230], look: 0.1, lean: 6, x: 134 },      // push it away
    { f: [150, 196], b: [140, 250], look: 0.0, lean: 2, x: 130 },      // swipe across
    { f: [164, 262], b: [128, 284], look: -0.15, lean: 0, x: 128 },    // rest
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
