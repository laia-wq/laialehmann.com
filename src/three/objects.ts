import * as THREE from 'three';
import { clay, palette } from './materials';

/**
 * Miniatures for the world inside the globe. Every object is built from a
 * few lathed or primitive shapes, in the shared clay material, and sits on
 * a small porcelain plinth. Each builder returns a group roughly 0.2 units tall.
 */

export type ObjectBuilder = () => THREE.Group;

function lathe(points: [number, number][], segments = 48): THREE.LatheGeometry {
  return new THREE.LatheGeometry(points.map(([x, y]) => new THREE.Vector2(x, y)), segments);
}

/** Smooth a coarse profile with a Catmull-Rom curve. */
function smoothProfile(points: [number, number][], samples = 40): [number, number][] {
  const curve = new THREE.SplineCurve(points.map(([x, y]) => new THREE.Vector2(x, y)));
  return curve.getPoints(samples).map((p) => [Math.max(0, p.x), p.y] as [number, number]);
}

export function plinth(radius = 0.12): THREE.Mesh {
  const r = radius;
  const m = new THREE.Mesh(
    lathe([
      [0, 0],
      [r - 0.004, 0],
      [r, 0.004],
      [r, 0.014],
      [r - 0.004, 0.018],
      [0, 0.018],
    ], 64),
    clay(palette.bone, 0.7),
  );
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

export function acorn(): THREE.Group {
  const g = new THREE.Group();

  const nut = new THREE.Mesh(
    lathe(
      smoothProfile([
        [0.0, 0.0],
        [0.03, 0.006],
        [0.062, 0.03],
        [0.078, 0.07],
        [0.079, 0.105],
        [0.074, 0.13],
      ]),
      64,
    ),
    clay(palette.clay, 0.5),
  );
  nut.castShadow = true;
  nut.receiveShadow = true;

  // Cap: a dome with a slightly flared rim that overhangs the nut.
  const cap = new THREE.Mesh(
    lathe(
      smoothProfile([
        [0.0, 0.178],
        [0.045, 0.172],
        [0.075, 0.155],
        [0.088, 0.135],
        [0.089, 0.12],
        [0.082, 0.114],
        [0.07, 0.118],
      ]).reverse(),
      64,
    ),
    clay(palette.clayDark, 0.75),
  );
  cap.castShadow = true;
  (cap.material as THREE.MeshPhysicalMaterial).side = THREE.DoubleSide;

  // Stem: a short tapered, slightly bent tube.
  const stemCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0.172, 0),
    new THREE.Vector3(0.004, 0.2, 0),
    new THREE.Vector3(0.016, 0.218, 0),
  ]);
  const stem = new THREE.Mesh(new THREE.TubeGeometry(stemCurve, 12, 0.0075, 10, false), clay(palette.clayDark, 0.75));
  stem.castShadow = true;
  const tip = new THREE.Mesh(new THREE.SphereGeometry(0.0075, 12, 8), stem.material);
  tip.position.copy(stemCurve.getPoint(1));

  const body = new THREE.Group();
  body.add(nut, cap, stem, tip);
  // Rest it at a gentle lean, as if it just landed.
  body.rotation.z = -0.32;
  body.position.set(0.012, 0.012, 0);
  g.add(body);

  const base = plinth(0.11);
  g.add(base);
  return g;
}

export const builders: Record<string, ObjectBuilder> = {
  acorn,
};
