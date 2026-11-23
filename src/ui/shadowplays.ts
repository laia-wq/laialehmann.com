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
    const sitLeg = (side: number) => {
      const hx = X(side * 2), kx = X(46 + side * 2), ky = hipY + 4;
      const fx = X(42 + side * 3);
      return { d: `M ${hx} ${hipY} L ${kx} ${ky} L ${fx} ${GROUND}`,
               shoe: `M ${fx - face * 6} ${GROUND - 6} Q ${fx + face * 4} ${GROUND - 9} ${fx + face * 15} ${GROUND - 1} L ${fx + face * 12} ${GROUND + 3} L ${fx - face * 7} ${GROUND + 3} Z` };
    };
    const lb = p.sit ? sitLeg(-1) : leg(-1), lf = p.sit ? sitLeg(1) : leg(1);
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


// ---------------------------------------------------------------- the first three
const tree = (x: number, base: number, h: number) =>
  `M ${x} ${base - h} L ${x + h * 0.22} ${base - h * 0.62} L ${x + h * 0.12} ${base - h * 0.62} L ${x + h * 0.3} ${base - h * 0.28} L ${x + h * 0.18} ${base - h * 0.28}
   L ${x + h * 0.36} ${base - h * 0.06} L ${x + 3} ${base - h * 0.06} L ${x + 3} ${base} L ${x - 3} ${base} L ${x - 3} ${base - h * 0.06}
   L ${x - h * 0.36} ${base - h * 0.06} L ${x - h * 0.18} ${base - h * 0.28} L ${x - h * 0.3} ${base - h * 0.28} L ${x - h * 0.12} ${base - h * 0.62} L ${x - h * 0.22} ${base - h * 0.62} Z`;

/** Forest loss: a hillside of pines; a patch of them comes down, a scan line
 *  sweeps over from above and boxes the gap it finds; then saplings grow back. */
export const forestPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  const hill = el('path', { stroke: 'none' }, room);
  hill.setAttribute('d', 'M -20 400 L -20 330 Q 80 300 160 318 Q 240 334 320 312 L 320 400 Z');
  const ground = (x: number) => (x < 160 ? 330 - (x + 20) / 180 * 30 + Math.sin((x + 20) / 180 * Math.PI) * -6 : 318 - (x - 160) / 160 * 6 + Math.sin((x - 160) / 160 * Math.PI) * 8);
  const trees = Array.from({ length: 13 }, (_, k) => {
    const x = -6 + k * 24 + (k % 3) * 4, h = 58 + ((k * 37) % 5) * 9;
    return { x, h, g: el('path', { stroke: 'none' }, room), cut: k >= 5 && k <= 8, order: k - 5 };
  });
  const scan = el('rect', { x: -20, width: 340, height: 3, stroke: 'none' }, room);
  const boxp = el('rect', { fill: 'none', 'stroke-width': 3, 'stroke-dasharray': '8 6' }, room);
  const LOOP = 12;
  return (time: number) => {
    const t = time % LOOP;
    for (const tr of trees) {
      const base = ground(tr.x) + 4;
      let fall = 0, grow = 1;
      if (tr.cut) {
        fall = seg(t, 1.0 + tr.order * 0.55, 1.6 + tr.order * 0.55);
        grow = seg(t, 8.0 + tr.order * 0.4, 10.6 + tr.order * 0.4);
      }
      const h = tr.h * (fall >= 1 ? Math.max(0.0001, grow) : 1) * (fall >= 1 && grow <= 0 ? 0 : 1);
      const ang = fall < 1 ? fall * 88 : 0;
      tr.g.setAttribute('d', tree(tr.x, base, Math.max(0.001, h)));
      tr.g.setAttribute('transform', `rotate(${ang} ${tr.x} ${base})`);
      tr.g.setAttribute('opacity', String(fall < 1 ? 1 - Math.max(0, fall - 0.8) * 5 : (grow > 0 ? 1 : 0)));
    }
    const sy = lerp(-20, 420, seg(t, 4.0, 6.0));
    scan.setAttribute('y', String(sy)); scan.setAttribute('opacity', String(t > 3.9 && t < 6.1 ? 0.8 : 0));
    const show = seg(t, 5.2, 5.8) * (1 - seg(t, 9.5, 10.5));
    boxp.setAttribute('x', '105'); boxp.setAttribute('y', '232'); boxp.setAttribute('width', '102'); boxp.setAttribute('height', '96');
    boxp.setAttribute('opacity', String(show)); boxp.setAttribute('stroke-dashoffset', String(t * 20));
  };
};

/** The physics lab: balls bouncing off the floor and walls, a pendulum, and
 *  a wireframe cube turning above them. */
export const physicsPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  el('rect', { x: -20, y: 372, width: 340, height: 6, stroke: 'none' }, room);
  const balls = [0, 1, 2].map((k) => ({ r: 14 + k * 5, T: 1.1 + k * 0.37, H: 150 - k * 30, vx: 38 + k * 19, ph: k * 0.7, g: el('ellipse', { stroke: 'none' }, room) }));
  const cube = el('path', { fill: 'none', 'stroke-width': 3 }, room);
  const pend = el('path', { fill: 'none', 'stroke-width': 3 }, room);
  const bob = el('circle', { r: 12, stroke: 'none' }, room);
  const V = [-1, 1].flatMap((x) => [-1, 1].flatMap((y) => [-1, 1].map((z) => [x, y, z])));
  const E = [[0, 1], [0, 2], [0, 4], [1, 3], [1, 5], [2, 3], [2, 6], [3, 7], [4, 5], [4, 6], [5, 7], [6, 7]];
  return (t: number) => {
    for (const b of balls) {
      const u = ((t + b.ph) / b.T) % 1;
      const y = 372 - b.r - b.H * 4 * u * (1 - u);
      const squash = u < 0.06 || u > 0.94 ? 0.82 : 1;
      const span = 300 - 2 * b.r, p = ((t + b.ph) * b.vx) % (2 * span);
      const x = b.r + (p < span ? p : 2 * span - p);
      b.g.setAttribute('cx', String(x)); b.g.setAttribute('cy', String(y + (1 - squash) * b.r));
      b.g.setAttribute('rx', String(b.r / Math.sqrt(squash))); b.g.setAttribute('ry', String(b.r * squash));
    }
    const a = t * 0.7, c = Math.cos(a), s_ = Math.sin(a), c2 = Math.cos(0.5), s2 = Math.sin(0.5);
    const pr = V.map(([x, y, z]) => { const X = x * c + z * s_, Z = -x * s_ + z * c, Y = y * c2 - Z * s2; return [230 + X * 34, 92 + Y * 34]; });
    set(cube, E.map(([i, j]) => `M ${pr[i][0]} ${pr[i][1]} L ${pr[j][0]} ${pr[j][1]}`).join(' '));
    const th = Math.sin(t * 2.1) * 0.6, px = 80, py = 40, L = 130;
    const bx = px + Math.sin(th) * L, by = py + Math.cos(th) * L;
    set(pend, `M ${px - 18} ${py} L ${px + 18} ${py} M ${px} ${py} L ${bx} ${by}`);
    bob.setAttribute('cx', String(bx)); bob.setAttribute('cy', String(by));
  };
};

/** Signwise: a hand close to the glass spelling out letters of the ASL
 *  alphabet, easing from one shape to the next. */
export const signPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  const arm = el('path', { stroke: 'none' }, room);
  const palm = el('path', { stroke: 'none' }, room);
  const fingers = [0, 1, 2, 3].map(() => el('path', { fill: 'none', 'stroke-width': 17 }, room));
  const thumb = el('path', { fill: 'none', 'stroke-width': 19 }, room);
  // per letter: curl of index, middle, ring, pinky (0 straight .. 1 folded), spread, thumb (angle, curl)
  const L: Record<string, number[]> = {
    A: [1, 1, 1, 1, 0, 0.15, 0.1], B: [0, 0, 0, 0, 0, 1.4, 0.9], C: [0.5, 0.5, 0.5, 0.5, 0, 0.7, 0.4], L: [0, 1, 1, 1, 0, -0.1, 0],
    V: [0, 0, 1, 1, 0.35, 1.1, 0.8], Y: [1, 1, 1, 0, 0.3, -0.2, 0], I: [1, 1, 1, 0, 0, 1.2, 0.8], W: [0, 0, 0, 1, 0.3, 1.2, 0.8],
  };
  const word = ['L', 'A', 'I', 'A', 'C', 'B', 'V', 'Y', 'W'];
  const DUR = 1.3;
  const cx = 150, cy = 250;
  const base = [[-30, -40], [-10, -46], [10, -44], [28, -36]];
  const len = [62, 68, 62, 48];
  return (time: number) => {
    const n = word.length, tt = time % (n * DUR), i = Math.floor(tt / DUR);
    const s_ = ease(Math.min(1, ((tt - i * DUR) / DUR) * 1.6));
    const A = L[word[i]], B = L[word[(i + 1) % n]];
    const v = A.map((a, k) => a + (B[k] - a) * s_);
    const sway = Math.sin(time * 0.9) * 3;
    set(arm, `M ${cx - 34} ${cy + 30} Q ${cx - 30} ${cy + 120} ${cx - 44} ${cy + 200} L ${cx + 40} ${cy + 200} Q ${cx + 30} ${cy + 120} ${cx + 34} ${cy + 30} Z`);
    set(palm, `M ${cx - 40 + sway} ${cy - 40} Q ${cx + sway} ${cy - 54} ${cx + 38 + sway} ${cy - 36} L ${cx + 36} ${cy + 34} Q ${cx} ${cy + 48} ${cx - 36} ${cy + 34} Z`);
    fingers.forEach((f, k) => {
      const curl = v[k], spread = (k === 1 ? -1 : k === 2 ? 1 : k === 0 ? -1.6 : 1.6) * v[4] * 0.5;
      const [bx, by] = [cx + base[k][0] + sway, cy + base[k][1]];
      const a1 = -Math.PI / 2 + spread, l1 = len[k] * 0.55, l2 = len[k] * 0.5;
      const m = [bx + Math.cos(a1 + curl * 1.6) * l1 * (1 - curl * 0.35), by + Math.sin(a1 + curl * 1.6) * l1 * (1 - curl * 0.35)];
      const a2 = a1 + curl * 3.0;
      const e = [m[0] + Math.cos(a2) * l2 * (1 - curl * 0.3), m[1] + Math.sin(a2) * l2 * (1 - curl * 0.3)];
      set(f, `M ${bx} ${by} L ${m[0]} ${m[1]} L ${e[0]} ${e[1]}`);
    });
    const ta = Math.PI + 0.6 - v[5] * 1.2, tc = v[6];
    const t0 = [cx - 34 + sway, cy + 12], t1 = [t0[0] + Math.cos(ta) * 40, t0[1] + Math.sin(ta) * 40];
    const t2 = [t1[0] + Math.cos(ta + tc * 1.8) * 30, t1[1] + Math.sin(ta + tc * 1.8) * 30];
    set(thumb, `M ${t0[0]} ${t0[1]} L ${t1[0]} ${t1[1]} L ${t2[0]} ${t2[1]}`);
  };
};

// ---------------------------------------------------------------- the sink-finding robot
/** A small robot rolls in, finds the sink, lifts a water filter jug under
 *  the tap; water runs; it lowers the jug and rolls off the way it came. */
export const robotPlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  el('rect', { x: 190, y: 250, width: 130, height: 12, stroke: 'none' }, room);            // counter top
  el('rect', { x: 200, y: 262, width: 120, height: 134, stroke: 'none', opacity: 0.0 }, room);
  el('path', { d: 'M 200 262 L 200 396 M 300 262 L 300 396', fill: 'none', 'stroke-width': 8 }, room);   // cabinet sides
  el('path', { d: 'M 228 250 L 228 206 Q 228 196 238 196 L 258 196 L 258 204', fill: 'none', 'stroke-width': 7 }, room); // tap
  el('rect', { x: 222, y: 216, width: 14, height: 6, rx: 2, stroke: 'none' }, room);
  const water = el('path', { fill: 'none', 'stroke-width': 4, 'stroke-dasharray': '10 6' }, room);
  const bot = el('g', {}, room);
  el('rect', { x: -26, y: -40, width: 52, height: 34, rx: 6, stroke: 'none' }, bot);        // body
  for (const wx of [-16, 16]) el('circle', { cx: wx, cy: -4, r: 9, stroke: 'none' }, bot);  // wheels
  el('path', { d: 'M 0 -40 L 0 -64', fill: 'none', 'stroke-width': 4 }, bot);                // mast
  el('rect', { x: -10, y: -76, width: 20, height: 13, rx: 3, stroke: 'none' }, bot);         // camera head
  const arm = el('path', { fill: 'none', 'stroke-width': 5 }, bot);
  const jug = el('path', { stroke: 'none' }, bot);
  const LOOP = 12;
  return (time: number) => {
    const t = time % LOOP;
    const x = lerp(lerp(-60, 196, seg(t, 0, 3)), -60, seg(t, 8.6, 11.6));
    const face = t > 8.6 ? -1 : 1;
    const bump = Math.abs(Math.sin(t * 9)) * 1.2 * ((t < 3 || t > 8.6) ? 1 : 0);
    bot.setAttribute('transform', `translate(${x} ${392 - bump}) scale(${face} 1)`);
    const up = seg(t, 3.3, 4.6) * (1 - seg(t, 7.4, 8.4));
    const ex = lerp(30, 40, up), ey = lerp(-34, -176, up);
    set(arm, `M 18 -30 L ${lerp(36, 30, up)} ${lerp(-30, -100, up)} L ${ex} ${ey}`);
    set(jug, `M ${ex - 2} ${ey - 4} L ${ex + 24} ${ey - 4} L ${ex + 22} ${ey + 30} L ${ex} ${ey + 30} Z M ${ex + 24} ${ey + 2} q 8 2 6 14 q -2 6 -6 6`);
    const on = t > 4.8 && t < 7.2 ? 1 : 0;
    set(water, `M 258 210 L 258 ${on ? 216 : 210}`);
    water.setAttribute('d', on ? 'M 258 210 L 258 222' : 'M 258 210 L 258 210');
    water.setAttribute('stroke-dashoffset', String(-t * 60));
    water.setAttribute('opacity', String(on));
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
  const who = person(room);
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
/** A cook behind a counter ladles soup from a steaming pot into a bowl and
 *  hands it across; the guest takes it and goes, the next one comes in. */
export const servePlay: Play = (svg, PW) => {
  const { room } = stage(svg, PW);
  el('rect', { x: 150, y: 286, width: 170, height: 12, stroke: 'none' }, room);    // counter
  el('rect', { x: 160, y: 298, width: 150, height: 98, stroke: 'none' }, room);
  const pot = el('path', { stroke: 'none' }, room);
  pot.setAttribute('d', 'M 238 286 L 238 254 L 292 254 L 292 286 Z M 232 254 L 298 254 L 298 248 L 232 248 Z');
  const steam = [0, 1, 2].map(() => el('path', { fill: 'none', 'stroke-width': 3 }, room));
  const cook = person(room);
  const guest = person(room);
  const ladle = el('path', { fill: 'none', 'stroke-width': 3 }, room);
  const bowl = el('path', { stroke: 'none' }, room);
  const LOOP = 12;
  return (time: number) => {
    const t = time % LOOP;
    steam.forEach((s_, k) => {
      const ph = (time * 0.5 + k / 3) % 1, x = 250 + k * 14, y = 244 - ph * 60;
      set(s_, `M ${x} ${y} q ${6 + Math.sin(time + k) * 4} -10 0 -20 q -6 -10 0 -20`);
      s_.setAttribute('opacity', String(Math.sin(ph * Math.PI) * 0.8));
    });
    // guest walks in (0..2.4), waits, takes the bowl (6..7), walks out (7.6..10.4)
    let gx = lerp(-60, 118, seg(t, 0, 2.4)); gx = lerp(gx, -70, seg(t, 7.6, 10.4));
    const gface = t > 7.6 ? -1 : 1, gwalk = (t < 2.4 || t > 7.6) ? 1 : 0;
    // cook: ladle into bowl (2.6..4.6), hold it out (4.6..6.4)
    const scoop = seg(t, 2.6, 3.4) * (1 - seg(t, 3.8, 4.4));
    const hold = seg(t, 4.4, 5.2) * (1 - seg(t, 6.2, 6.8));
    const taken = t > 6.4 && t < 10.6;
    const cx = 268;
    const ladH: [number, number] = [lerp(250, 262, scoop), lerp(230, 246, scoop)];
    const bowlCook: [number, number] = [lerp(222, 172, hold), 262];
    cook({ x: cx, face: -1, walk: 0, ph: 0, lean: 3 + hold * 6, look: -0.2,
      hand: hold > 0.01 ? [bowlCook[0], bowlCook[1] + 4] : ladH, hand2: [bowlCook[0] + 8, bowlCook[1] + 6] });
    set(ladle, hold > 0.01 ? '' : `M ${ladH[0]} ${ladH[1]} L ${ladH[0] - 6} ${ladH[1] + 34}`);
    const [hx, hy] = taken ? [gx + gface * 26, 250] : bowlCook;
    const gHands: [[number, number], [number, number]] = taken ? [[hx, hy + 6], [hx - gface * 8, hy + 8]] :
      (t > 5.4 && t < 6.6 ? [[lerp(gx + 20, 176, seg(t, 5.4, 6.2)), lerp(300, 266, seg(t, 5.4, 6.2))], [gx - 6, 298]] : [[gx + gface * 6 + Math.sin(t * 7.5) * 12 * gwalk, 300], [gx - gface * 6, 298]]);
    guest({ x: gx, face: gface as 1 | -1, walk: gwalk, ph: t * 7.5, hand: gHands[0], hand2: gHands[1], look: taken ? -0.15 : 0.05 });
    const show = t > 3.6 && t < 10.8;
    set(bowl, show ? `M ${hx - 13} ${hy - 2} Q ${hx} ${hy + 14} ${hx + 13} ${hy - 2} Z` : '');
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
  el('feGaussianBlur', { stdDeviation: 9 }, f);
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
      const x = 92 + k * 30, h = (90 + (k % 3) * 40) * burn * (0.85 + 0.15 * Math.sin(t * 9 + k * 2)), w = 22 + (k % 2) * 8;
      const sw = Math.sin(t * 5 + k) * 8;
      set(p, `M ${x - w} 380 Q ${x - w} ${380 - h * 0.5} ${x + sw} ${380 - h} Q ${x + w} ${380 - h * 0.5} ${x + w} 380 Z`);
      p.setAttribute('opacity', String(burn * 0.85));
    });
  };
};
