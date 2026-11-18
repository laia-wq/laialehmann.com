import * as THREE from 'three';

/** Canvas texture for the engraved plaque: name + discipline, letterpress look. */
export async function plaqueTexture(name: string, role: string): Promise<THREE.CanvasTexture> {
  try {
    await Promise.all([
      document.fonts.load('500 120px "Cormorant Garamond"'),
      document.fonts.load('500 40px "Inter Variable"'),
    ]);
  } catch {
    /* fall back to system fonts */
  }
  const W = 1024, H = 320;
  const c = document.createElement('canvas');
  c.width = W;
  c.height = H;
  const g = c.getContext('2d')!;
  g.fillStyle = '#d9d0c3';
  g.fillRect(0, 0, W, H);
  // Hairline border inset.
  g.strokeStyle = 'rgba(70,55,40,0.35)';
  g.lineWidth = 2;
  g.strokeRect(18, 18, W - 36, H - 36);

  const engrave = (text: string, font: string, y: number, spacing = 0) => {
    g.font = font;
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    (g as CanvasRenderingContext2D & { letterSpacing?: string }).letterSpacing = `${spacing}px`;
    // Highlight below-right, shadow above-left: reads as cut into the surface.
    g.fillStyle = 'rgba(255,250,240,0.7)';
    g.fillText(text, W / 2 + 1.5, y + 2);
    g.fillStyle = 'rgba(60,45,32,0.9)';
    g.fillText(text, W / 2, y);
  };
  engrave(name, '500 118px "Cormorant Garamond", Georgia, serif', H * 0.43, 2);
  engrave(role.toUpperCase(), '500 30px "Inter Variable", system-ui, sans-serif', H * 0.75, 9);

  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}
