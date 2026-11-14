/**
 * Photo measurement on the ground plane.
 *
 * A known flat object on the ground (a sheet of paper, a patio slab) gives four image
 * points with known real positions. The homography between them maps every pixel of the
 * ground to real units, which corrects perspective: ground far from the camera looks
 * smaller in the photo but is measured at its true size.
 *
 * This module has no browser or framework imports so it can be tested with plain Node.
 */

export type Point = { x: number; y: number };
/** Row-major 3x3 matrix. */
export type Matrix3 = number[];

export type ReferenceObject = {
  id: string;
  label: string;
  /** Short side and long side, in `unit`. */
  width: number;
  length: number;
  unit: "ft" | "m";
};

export const REFERENCE_OBJECTS: ReferenceObject[] = [
  { id: "letter", label: "Letter paper (8.5 × 11 in)", width: 8.5 / 12, length: 11 / 12, unit: "ft" },
  { id: "a4", label: "A4 paper (21 × 29.7 cm)", width: 0.21, length: 0.297, unit: "m" },
  { id: "slab-24", label: "Patio slab (24 × 24 in)", width: 2, length: 2, unit: "ft" },
  { id: "slab-18", label: "Patio slab (18 × 18 in)", width: 1.5, length: 1.5, unit: "ft" },
  { id: "plywood", label: "Plywood sheet (4 × 8 ft)", width: 4, length: 8, unit: "ft" },
];

const FEET_PER_METRE = 3.28084;

export function convertLength(value: number, from: "ft" | "m", to: "ft" | "m") {
  if (from === to) return value;
  return from === "m" ? value * FEET_PER_METRE : value / FEET_PER_METRE;
}

function multiply(a: Matrix3, b: Matrix3): Matrix3 {
  const out = new Array(9).fill(0);
  for (let r = 0; r < 3; r += 1)
    for (let c = 0; c < 3; c += 1)
      for (let k = 0; k < 3; k += 1) out[r * 3 + c] += a[r * 3 + k] * b[k * 3 + c];
  return out;
}

export function determinant(m: Matrix3) {
  return m[0] * (m[4] * m[8] - m[5] * m[7]) - m[1] * (m[3] * m[8] - m[5] * m[6]) + m[2] * (m[3] * m[7] - m[4] * m[6]);
}

export function invert(m: Matrix3): Matrix3 | null {
  const det = determinant(m);
  if (!Number.isFinite(det) || Math.abs(det) < 1e-12) return null;
  const inv = [
    m[4] * m[8] - m[5] * m[7], m[2] * m[7] - m[1] * m[8], m[1] * m[5] - m[2] * m[4],
    m[5] * m[6] - m[3] * m[8], m[0] * m[8] - m[2] * m[6], m[2] * m[3] - m[0] * m[5],
    m[3] * m[7] - m[4] * m[6], m[1] * m[6] - m[0] * m[7], m[0] * m[4] - m[1] * m[3],
  ];
  return inv.map((value) => value / det);
}

export function apply(m: Matrix3, p: Point): Point | null {
  const w = m[6] * p.x + m[7] * p.y + m[8];
  if (Math.abs(w) < 1e-12) return null;
  return { x: (m[0] * p.x + m[1] * p.y + m[2]) / w, y: (m[3] * p.x + m[4] * p.y + m[5]) / w };
}

/** Similarity transform that centres points and scales their mean distance to √2. */
function normalizer(points: Point[]): Matrix3 {
  const cx = points.reduce((sum, p) => sum + p.x, 0) / points.length;
  const cy = points.reduce((sum, p) => sum + p.y, 0) / points.length;
  const mean = points.reduce((sum, p) => sum + Math.hypot(p.x - cx, p.y - cy), 0) / points.length || 1;
  const s = Math.SQRT2 / mean;
  return [s, 0, -s * cx, 0, s, -s * cy, 0, 0, 1];
}

/** Solve the 8x8 linear system with partial pivoting. */
function solveLinear(a: number[][], b: number[]): number[] | null {
  const n = b.length;
  const m = a.map((row, i) => [...row, b[i]]);
  for (let col = 0; col < n; col += 1) {
    let pivot = col;
    for (let row = col + 1; row < n; row += 1) if (Math.abs(m[row][col]) > Math.abs(m[pivot][col])) pivot = row;
    if (Math.abs(m[pivot][col]) < 1e-12) return null;
    [m[col], m[pivot]] = [m[pivot], m[col]];
    for (let row = 0; row < n; row += 1) {
      if (row === col) continue;
      const factor = m[row][col] / m[col][col];
      for (let k = col; k <= n; k += 1) m[row][k] -= factor * m[col][k];
    }
  }
  return m.map((row, i) => row[n] / row[i]);
}

/** Homography mapping each `from` point to the matching `to` point (exactly four pairs). */
export function solveHomography(from: Point[], to: Point[]): Matrix3 | null {
  if (from.length !== 4 || to.length !== 4) return null;
  const tFrom = normalizer(from);
  const tTo = normalizer(to);
  const src = from.map((p) => apply(tFrom, p) as Point);
  const dst = to.map((p) => apply(tTo, p) as Point);
  const rows: number[][] = [];
  const rhs: number[] = [];
  for (let i = 0; i < 4; i += 1) {
    const { x, y } = src[i];
    const { x: u, y: v } = dst[i];
    rows.push([x, y, 1, 0, 0, 0, -u * x, -u * y]);
    rhs.push(u);
    rows.push([0, 0, 0, x, y, 1, -v * x, -v * y]);
    rhs.push(v);
  }
  const h = solveLinear(rows, rhs);
  const toInverse = invert(tTo);
  if (!h || !toInverse) return null;
  const result = multiply(toInverse, multiply([...h, 1], tFrom));
  return result.map((value) => value / result[8]);
}

/** Sort four points into a consistent clockwise order around their centre. */
export function orderCorners(points: Point[]): Point[] {
  const cx = points.reduce((sum, p) => sum + p.x, 0) / points.length;
  const cy = points.reduce((sum, p) => sum + p.y, 0) / points.length;
  return [...points].sort((a, b) => Math.atan2(a.y - cy, a.x - cx) - Math.atan2(b.y - cy, b.x - cx));
}

function polygonArea(points: Point[]) {
  let area = 0;
  for (let i = 0; i < points.length; i += 1) {
    const a = points[i];
    const b = points[(i + 1) % points.length];
    area += a.x * b.y - b.x * a.y;
  }
  return Math.abs(area) / 2;
}

/**
 * Image-to-ground homography from the four corners of a known rectangle.
 *
 * For a non-square object the photo alone does not say which side is the long one.
 * Both assignments are tried and the one that best fits a normal phone camera (square
 * pixels, centred lens, roughly 26 mm equivalent) wins.
 */
export function groundHomography(
  corners: Point[],
  object: { width: number; length: number },
  imageSize: { width: number; height: number },
): Matrix3 | null {
  if (corners.length !== 4) return null;
  const ordered = orderCorners(corners);
  if (polygonArea(ordered) < 16) return null;
  const { width: w, length: l } = object;
  const options = [
    [{ x: 0, y: 0 }, { x: w, y: 0 }, { x: w, y: l }, { x: 0, y: l }],
    [{ x: 0, y: 0 }, { x: l, y: 0 }, { x: l, y: w }, { x: 0, y: w }],
  ];
  const cx = imageSize.width / 2;
  const cy = imageSize.height / 2;
  const focal = 0.75 * Math.max(imageSize.width, imageSize.height);
  let best: { h: Matrix3; score: number } | null = null;
  for (const ground of Math.abs(w - l) < 1e-9 ? options.slice(0, 1) : options) {
    const imageToGround = solveHomography(ordered, ground);
    const groundToImage = solveHomography(ground, ordered);
    if (!imageToGround || !groundToImage) continue;
    // Columns of the ground-to-image homography, in camera coordinates.
    const g = groundToImage;
    const column = (c: number) => {
      const z = g[6 + c];
      return [(g[c] - cx * z) / focal, (g[3 + c] - cy * z) / focal, z];
    };
    const c1 = column(0);
    const c2 = column(1);
    const n1 = Math.hypot(c1[0], c1[1], c1[2]);
    const n2 = Math.hypot(c2[0], c2[1], c2[2]);
    const orthogonality = Math.abs(c1[0] * c2[0] + c1[1] * c2[1] + c1[2] * c2[2]) / (n1 * n2);
    const score = Math.abs(Math.log(n1 / n2)) + orthogonality;
    if (!best || score < best.score) best = { h: imageToGround, score };
  }
  return best?.h ?? null;
}

/** Real length of the object's long side in image pixels, averaged over both long edges. */
export function longSidePixels(corners: Point[]) {
  const o = orderCorners(corners);
  const sides = [0, 1, 2, 3].map((i) => Math.hypot(o[(i + 1) % 4].x - o[i].x, o[(i + 1) % 4].y - o[i].y));
  return Math.max((sides[0] + sides[2]) / 2, (sides[1] + sides[3]) / 2);
}

// Marching-squares segments between edge midpoints: 0 top, 1 right, 2 bottom, 3 left.
const SEGMENTS: number[][][] = [
  [], [[3, 2]], [[2, 1]], [[3, 1]], [[0, 1]], [[3, 0], [2, 1]], [[0, 2]], [[3, 0]],
  [[3, 0]], [[0, 2]], [[0, 1], [3, 2]], [[0, 1]], [[3, 1]], [[2, 1]], [[3, 2]], [],
];

export type GroundMeasurement = {
  selectedPixelCount: number;
  /** Area and outline length in real units; undefined when not calibrated. */
  area?: number;
  perimeter?: number;
  /** True when part of the selection is at or above the horizon of the ground plane. */
  beyondGround: boolean;
};

/**
 * Measure a selection (1 = selected) either with a homography to the ground or a single
 * uniform scale (real units per pixel). The outline follows marching squares, so
 * diagonal edges are not counted as a pixel staircase.
 */
export function measureSelection(
  selected: Uint8Array,
  width: number,
  height: number,
  calibration?: { homography: Matrix3 } | { unitsPerPixel: number },
): GroundMeasurement {
  const homography = calibration && "homography" in calibration ? calibration.homography : undefined;
  const scale = calibration && "unitsPerPixel" in calibration ? calibration.unitsPerPixel : undefined;
  let count = 0;
  let area = 0;
  let beyondGround = false;
  const detH = homography ? determinant(homography) : 0;
  // The sign of w that belongs to the visible ground (where the object lies).
  let groundSign = 0;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (!selected[y * width + x]) continue;
      count += 1;
      if (!homography) continue;
      const w = homography[6] * (x + 0.5) + homography[7] * (y + 0.5) + homography[8];
      if (!groundSign) groundSign = Math.sign(w);
      if (Math.sign(w) !== groundSign || Math.abs(w) < 1e-9) {
        beyondGround = true;
        continue;
      }
      area += Math.abs(detH / (w * w * w));
    }
  }
  if (!calibration) return { selectedPixelCount: count, beyondGround: false };

  const at = (x: number, y: number) => (x >= 0 && y >= 0 && x < width && y < height ? selected[y * width + x] : 0);
  let perimeter = 0;
  for (let y = -1; y < height; y += 1) {
    for (let x = -1; x < width; x += 1) {
      const index = (at(x, y) << 3) | (at(x + 1, y) << 2) | (at(x + 1, y + 1) << 1) | at(x, y + 1);
      const segments = SEGMENTS[index];
      if (!segments.length) continue;
      // Pixel centres sit at +0.5; edge midpoints of the cell between them:
      const mid = [
        { x: x + 1, y: y + 0.5 }, { x: x + 1.5, y: y + 1 }, { x: x + 1, y: y + 1.5 }, { x: x + 0.5, y: y + 1 },
      ];
      for (const [a, b] of segments) {
        if (homography) {
          const pa = apply(homography, mid[a]);
          const pb = apply(homography, mid[b]);
          if (pa && pb) perimeter += Math.hypot(pb.x - pa.x, pb.y - pa.y);
        } else {
          perimeter += Math.hypot(mid[b].x - mid[a].x, mid[b].y - mid[a].y) * (scale as number);
        }
      }
    }
  }
  return {
    selectedPixelCount: count,
    area: homography ? area : count * (scale as number) ** 2,
    perimeter,
    beyondGround,
  };
}

function convexHull(points: Point[]): Point[] {
  const sorted = [...points].sort((a, b) => a.x - b.x || a.y - b.y);
  const cross = (o: Point, a: Point, b: Point) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lower: Point[] = [];
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper: Point[] = [];
  for (const p of [...sorted].reverse()) {
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  return [...lower.slice(0, -1), ...upper.slice(0, -1)];
}

/**
 * Largest quadrilateral with corners on the hull: every pair of hull points is tried as a
 * diagonal, with the farthest point on each side of it as the other two corners.
 */
function quadFromHull(points: Point[]): Point[] | null {
  if (points.length < 4) return null;
  // Hulls of pixel outlines are small, but cap the work for very large objects.
  const stride = Math.ceil(points.length / 120);
  const hull = points.filter((_, i) => i % stride === 0);
  let best: { quad: Point[]; area: number } | null = null;
  for (let i = 0; i < hull.length; i += 1) {
    for (let j = i + 2; j < hull.length; j += 1) {
      const a = hull[i];
      const c = hull[j];
      let left: Point | null = null;
      let right: Point | null = null;
      let maxLeft = 0;
      let maxRight = 0;
      for (const p of hull) {
        const side = (c.x - a.x) * (p.y - a.y) - (c.y - a.y) * (p.x - a.x);
        if (side > maxLeft) [maxLeft, left] = [side, p];
        if (-side > maxRight) [maxRight, right] = [-side, p];
      }
      const area = (maxLeft + maxRight) / 2;
      if (left && right && (!best || area > best.area)) best = { quad: [a, left, c, right], area };
    }
  }
  return best ? orderCorners(best.quad) : null;
}

/**
 * Find a flat, evenly coloured object (a sheet of paper, a slab) around a tapped point and
 * return its four corners in image pixels, or null when no clean four-sided shape is found.
 */
export function detectReferenceObject(
  pixels: Uint8ClampedArray,
  width: number,
  height: number,
  seed: Point,
): Point[] | null {
  const sx = Math.round(seed.x);
  const sy = Math.round(seed.y);
  if (sx < 0 || sy < 0 || sx >= width || sy >= height) return null;
  let r = 0;
  let g = 0;
  let b = 0;
  let n = 0;
  for (let y = sy - 2; y <= sy + 2; y += 1)
    for (let x = sx - 2; x <= sx + 2; x += 1) {
      if (x < 0 || y < 0 || x >= width || y >= height) continue;
      const i = (y * width + x) * 4;
      r += pixels[i]; g += pixels[i + 1]; b += pixels[i + 2]; n += 1;
    }
  r /= n; g /= n; b /= n;
  const tolerance = 38;
  const limit = Math.floor(width * height * 0.3);
  const visited = new Uint8Array(width * height);
  const queue = new Int32Array(limit + 1);
  let head = 0;
  let tail = 0;
  queue[tail++] = sy * width + sx;
  visited[sy * width + sx] = 1;
  const boundary: Point[] = [];
  let size = 0;
  while (head < tail) {
    const index = queue[head++];
    size += 1;
    const x = index % width;
    const y = (index - x) / width;
    let edge = false;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = x + dx;
      const ny = y + dy;
      if (nx < 0 || ny < 0 || nx >= width || ny >= height) return null; // touches the frame: not an object
      const ni = ny * width + nx;
      if (visited[ni]) continue;
      const p = ni * 4;
      if (Math.hypot(pixels[p] - r, pixels[p + 1] - g, pixels[p + 2] - b) > tolerance) {
        edge = true;
        continue;
      }
      if (tail >= limit) return null; // too large to be a reference object
      visited[ni] = 1;
      queue[tail++] = ni;
    }
    if (edge) boundary.push({ x: x + 0.5, y: y + 0.5 });
  }
  if (size < 60) return null;
  const quad = quadFromHull(convexHull(boundary));
  if (!quad) return null;
  // A clean rectangle in perspective fills most of its four-sided outline.
  const fill = size / polygonArea(quad);
  if (fill < 0.8 || fill > 1.25) return null;
  return refineCorners(quad, boundary) ?? quad;
}

/** Fit a straight line through the edge pixels of each side and intersect neighbouring sides. */
function refineCorners(quad: Point[], boundary: Point[]): Point[] | null {
  const lines: { point: Point; direction: Point }[] = [];
  for (let side = 0; side < 4; side += 1) {
    const a = quad[side];
    const b = quad[(side + 1) % 4];
    const length = Math.hypot(b.x - a.x, b.y - a.y);
    if (length < 4) return null;
    const ux = (b.x - a.x) / length;
    const uy = (b.y - a.y) / length;
    // Use the middle 80% of the side so rounded or trodden corners do not bend the line.
    const near = boundary.filter((p) => {
      const along = (p.x - a.x) * ux + (p.y - a.y) * uy;
      const across = Math.abs((p.x - a.x) * uy - (p.y - a.y) * ux);
      return across < 2.5 && along > length * 0.1 && along < length * 0.9;
    });
    if (near.length < 6) return null;
    const mx = near.reduce((sum, p) => sum + p.x, 0) / near.length;
    const my = near.reduce((sum, p) => sum + p.y, 0) / near.length;
    let sxx = 0;
    let sxy = 0;
    let syy = 0;
    for (const p of near) {
      sxx += (p.x - mx) ** 2;
      sxy += (p.x - mx) * (p.y - my);
      syy += (p.y - my) ** 2;
    }
    const angle = 0.5 * Math.atan2(2 * sxy, sxx - syy);
    lines.push({ point: { x: mx, y: my }, direction: { x: Math.cos(angle), y: Math.sin(angle) } });
  }
  const corners: Point[] = [];
  for (let i = 0; i < 4; i += 1) {
    const l1 = lines[(i + 3) % 4];
    const l2 = lines[i];
    const denominator = l1.direction.x * l2.direction.y - l1.direction.y * l2.direction.x;
    if (Math.abs(denominator) < 1e-6) return null;
    const t = ((l2.point.x - l1.point.x) * l2.direction.y - (l2.point.y - l1.point.y) * l2.direction.x) / denominator;
    const corner = { x: l1.point.x + t * l1.direction.x, y: l1.point.y + t * l1.direction.y };
    // Edge pixels sit half a pixel inside the object; refined corners must stay near the rough ones.
    if (Math.hypot(corner.x - quad[i].x, corner.y - quad[i].y) > 6) return null;
    corners.push(corner);
  }
  return corners;
}

/**
 * Share of the selection's outline that borders grey, hard surfaces (paths, patios, walls,
 * kerbs). The AI tends to continue those surfaces into the selection, so the editor warns.
 * Edges along the photo frame are ignored.
 */
export function hardscapeEdgeShare(
  pixels: Uint8ClampedArray,
  selected: Uint8Array,
  width: number,
  height: number,
): { share: number; touchingLength: number } {
  const reach = Math.max(6, Math.round(Math.min(width, height) / 40));
  const hard = (x: number, y: number) => {
    const i = (y * width + x) * 4;
    const r = pixels[i];
    const g = pixels[i + 1];
    const b = pixels[i + 2];
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    if (max < 70) return false; // deep shadow or joints: unknown
    // Sunlit concrete, pavers and stone are grey; in shade they take on the blue of the sky.
    // Grass is green and soil or mulch is brown, so neither passes.
    return (max >= 95 && (max - min) / max < 0.16) || (b >= g && b > r + 15);
  };
  let edges = 0;
  let touching = 0;
  const step = Math.max(1, Math.round(Math.min(width, height) / 400));
  for (let y = step; y < height - step; y += step) {
    for (let x = step; x < width - step; x += step) {
      if (!selected[y * width + x]) continue;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        if (selected[(y + dy * step) * width + (x + dx * step)]) continue;
        edges += 1;
        let hardCount = 0;
        let samples = 0;
        for (let d = 2; d <= reach; d += 1) {
          const nx = x + dx * d;
          const ny = y + dy * d;
          if (nx < 0 || ny < 0 || nx >= width || ny >= height) break;
          if (selected[ny * width + nx]) break;
          samples += 1;
          hardCount += Number(hard(nx, ny));
        }
        if (samples >= 2 && hardCount / samples >= 0.4) touching += 1;
        break;
      }
    }
  }
  return { share: edges ? touching / edges : 0, touchingLength: touching * step };
}
