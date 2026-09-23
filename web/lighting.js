// Pixel-art lighting: colored point lights + moon, per-object computed shadows.
//
// Model (all at native resolution, no filtering):
//  - Shadow strength fades with distance from the casting column's ground point (full at the
//    contact, cfg.fadeTo at the tip), and shadow masks are blurred (cfg.blur) for soft edges;
//    light and shadow values are posterized into flat bands (cfg.levels), no dithering.
//  - Every standing object is a billboard on its ground line. A sprite pixel's height above
//    the ground is its distance above that line. Each pixel's 4 corners are projected onto
//    the floor away from a light (point light: P + (P - L) * h / (Lh - h); moon: P + dir * h),
//    and the projected quad is rasterized into that light's shadow mask. Walls are boxes.
//  - Each light is a texture: falloff posterized into flat bands, shadows cut out.
//    Lights and props are static, so these are baked once; flicker only scales intensity.
//  - Per frame: floor *= ambient + sum(lights with shadows); objects *= ambient +
//    sum(lights without shadows) (no self-shadowing); the hero's shadow is projected per
//    frame from its current animation frame; emissive pixels are drawn unlit on top.

// Flat-shaded bands: round a 0..1 value to `n` steps (no dithering).
const band = (v, n) => Math.round(v * n) / n;

function rgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function canvas(w, h) {
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  const ctx = c.getContext("2d", { willReadFrequently: true });
  ctx.imageSmoothingEnabled = false;
  return [c, ctx];
}

// Opaque-pixel mask of an image region.
const maskCache = new Map();
export function alphaMask(img, x, y, w, h) {
  const key = `${img.src}|${x}|${y}|${w}|${h}`;
  if (maskCache.has(key)) return maskCache.get(key);
  const [, c] = canvas(w, h);
  c.drawImage(img, x, y, w, h, 0, 0, w, h);
  const d = c.getImageData(0, 0, w, h).data;
  const m = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) m[i] = d[i * 4 + 3] > 127 ? 1 : 0;
  maskCache.set(key, m);
  return m;
}

// Write value(cx, cy) (max-combined) for pixels whose centers fall inside convex polygon
// `pts` ([[x,y],...]) into the Float32 mask (W x H, origin ox, oy).
function fillConvex(mask, W, H, pts, ox = 0, oy = 0, value = () => 1) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [x, y] of pts) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
  x0 = Math.max(0, Math.floor(x0 - ox)); y0 = Math.max(0, Math.floor(y0 - oy));
  x1 = Math.min(W - 1, Math.ceil(x1 - ox)); y1 = Math.min(H - 1, Math.ceil(y1 - oy));
  const n = pts.length;
  for (let py = y0; py <= y1; py++) {
    const cy = py + 0.5 + oy;
    // Intersect the edge half-planes once per scanline, rather than testing every
    // pixel in the bounding box. Keep both windings (including degenerate quads)
    // and the original cross-product tolerance at pixel centers.
    let loP = x0, hiP = x1, loN = x0, hiN = x1;
    for (let i = 0; i < n; i++) {
      const [ax, ay] = pts[i], [bx, by] = pts[(i + 1) % n];
      const dy = by - ay, c = (bx - ax) * (cy - ay) - dy * (ox + 0.5 - ax);
      if (dy > 0) {
        hiP = Math.min(hiP, (c + 1e-6) / dy);
        loN = Math.max(loN, (c - 1e-6) / dy);
      } else if (dy < 0) {
        loP = Math.max(loP, (c + 1e-6) / dy);
        hiN = Math.min(hiN, (c - 1e-6) / dy);
      } else {
        if (c < -1e-6) hiP = -Infinity;
        if (c > 1e-6) hiN = -Infinity;
      }
      if (loP > hiP && loN > hiN) break;
    }
    const endP = Math.floor(hiP), endN = Math.floor(hiN);
    for (let px = Math.ceil(loP); px <= endP; px++) {
      const i = py * W + px;
      mask[i] = Math.max(mask[i], value(px + 0.5 + ox, cy));
    }
    for (let px = Math.ceil(loN); px <= endN; px++) {
      if (px >= loP && px <= endP) continue;
      const i = py * W + px;
      mask[i] = Math.max(mask[i], value(px + 0.5 + ox, cy));
    }
  }
  // thin quads: always mark the pixels under the projected corners
  for (const [x, y] of pts) {
    const px = Math.floor(x - ox), py = Math.floor(y - oy);
    if (px >= 0 && py >= 0 && px < W && py < H) {
      const i = py * W + px;
      mask[i] = Math.max(mask[i], value(px + 0.5 + ox, py + 0.5 + oy));
    }
  }
}

// Separable box blur (radius r), `passes` times: soft shadow edges (penumbra).
function blur(m, W, H, r = 1, passes = 2, tmp = new Float32Array(m.length)) {
  const n = 2 * r + 1;
  for (let p = 0; p < passes; p++) {
    if (r === 1) {
      // The usual penumbra: keep the same addition order and Float32 rounding,
      // but avoid a clamped inner kernel loop for each sample.
      for (let y = 0; y < H; y++) {
        const row = y * W;
        for (let x = 0; x < W; x++) {
          const i = row + x;
          tmp[i] = (m[x ? i - 1 : i] + m[i] + m[x + 1 < W ? i + 1 : i]) / 3;
        }
      }
      for (let y = 0; y < H; y++) {
        const row = y * W, above = Math.max(0, y - 1) * W, below = Math.min(H - 1, y + 1) * W;
        for (let x = 0; x < W; x++) m[row + x] = (tmp[above + x] + tmp[row + x] + tmp[below + x]) / 3;
      }
      continue;
    }
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      let s = 0;
      for (let k = -r; k <= r; k++) { const xx = Math.min(W - 1, Math.max(0, x + k)); s += m[y * W + xx]; }
      tmp[y * W + x] = s / n;
    }
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      let s = 0;
      for (let k = -r; k <= r; k++) { const yy = Math.min(H - 1, Math.max(0, y + k)); s += tmp[yy * W + x]; }
      m[y * W + x] = s / n;
    }
  }
  return m;
}

// Clamp first, then round nonnegative band indices with integer truncation.
// Accumulators are Float32; the small integer band count keeps this exact.
function writeLightBands(D, VW, levels, y0, y1) {
  const a = D.ia.data, b = D.ib.data, al = D.accLit, ar = D.accRaw, bands = D.bands;
  for (let y = y0; y < y1; y++) {
    const end = (y * VW + D.active[y * 2 + 1]) * 3;
    for (let i = (y * VW + D.active[y * 2]) * 3, j = i / 3 * 4; i < end; i += 3, j += 4) {
      a[j] = bands[(Math.max(0, Math.min(1, al[i])) * levels + 0.5) | 0];
      b[j] = bands[(Math.max(0, Math.min(1, ar[i])) * levels + 0.5) | 0];
      a[j + 1] = bands[(Math.max(0, Math.min(1, al[i + 1])) * levels + 0.5) | 0];
      b[j + 1] = bands[(Math.max(0, Math.min(1, ar[i + 1])) * levels + 0.5) | 0];
      a[j + 2] = bands[(Math.max(0, Math.min(1, al[i + 2])) * levels + 0.5) | 0];
      b[j + 2] = bands[(Math.max(0, Math.min(1, ar[i + 2])) * levels + 0.5) | 0];
    }
  }
}

function hull(pts) {
  const p = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo = [], up = [];
  for (const q of p) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
  for (const q of p.reverse()) { while (up.length >= 2 && cross(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
  return lo.slice(0, -1).concat(up.slice(0, -1));
}

export class Lighting {
  // cfg: { ambient, moon: {color, dir:[x,y], length, shadow}, shadow, levels, maxShadow, fadeTo, blur }
  // light: { x, y, h, color, radius, intensity, flicker?(t), owner?, shadow? (strength scale),
  //          maxShadow? (px) }
  constructor({ W, H, cfg, lights, occluders, walls }) {
    Object.assign(this, { W, H, cfg, lights, occluders, walls });
    // wall tops are above the shadows they cast: never shade wall pixels
    this.wallMask = new Uint8Array(W * H);
    for (const o of walls) for (let y = o.y0; y < o.y1; y++) for (let x = o.x0; x < o.x1; x++) this.wallMask[y * W + x] = 1;
    this.ambient = rgb(cfg.ambient);
    [this.floorL, this.floorLctx] = canvas(1, 1);
  }

  // Project ground point (gx, gy) at height h away from light (null light = moon).
  project(light, gx, gy, h) {
    if (h <= 0) return [gx, gy];
    const max = (light && light.maxShadow) || this.cfg.maxShadow;
    if (!light) {
      const [dx, dy] = this.cfg.moon.dir, k = this.cfg.moon.length * h;
      return [gx + dx * k, gy + dy * k];
    }
    const vx = gx - light.x, vy = gy - light.y, dist = Math.hypot(vx, vy) || 1;
    const denom = light.h - h;
    let t = denom > 0.25 ? h / denom : Infinity;
    t = Math.min(t, max / dist);
    return [gx + vx * t, gy + vy * t];
  }

  // Rasterize an occluder's shadow for `light` into mask (mw x mh, origin ox, oy).
  castShadow(mask, mw, mh, ox, oy, light, o) {
    if (light) {
      // Projection travels away from the light, by at most maxShadow. Include
      // the ground footprint and thin-quad corner pixels in this conservative bound.
      const reach = light.maxShadow || this.cfg.maxShadow;
      const x1 = o.box ? o.x1 : o.x0 + o.w;
      const y0 = o.box ? o.y0 : o.groundY, y1 = o.box ? o.y1 : o.groundY;
      if (x1 + (light.x < x1 ? reach : 0) < ox ||
          o.x0 - (light.x > o.x0 ? reach : 0) >= ox + mw ||
          y1 + (light.y < y1 ? reach : 0) < oy ||
          y0 - (light.y > y0 ? reach : 0) >= oy + mh) return;
    }
    if (o.box) {  // wall: footprint rect extruded to height o.h
      const { x0, y0, x1, y1, h } = o;
      const pts = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
      const all = pts.concat(pts.map(([x, y]) => this.project(light, x, y, h)));
      fillConvex(mask, mw, mh, hull(all), ox, oy);
      return;
    }
    const { x0, y0, w, h, m, groundY } = o;
    // fade: full strength at the contact point, `fadeTo` at the tip of the object's
    // tallest projection, so every object's shadow thins out the same way
    const cx = x0 + w / 2, [tx, ty] = this.project(light, cx, groundY, groundY - y0);
    const fadeLen = Math.max(4, Math.hypot(tx - cx, ty - groundY)), fadeTo = this.cfg.fadeTo ?? 0.15;
    // one quad per vertical run of opaque pixels in a column (union of its pixel quads)
    for (let sx = 0; sx < w; sx++) {
      let sy = 0;
      while (sy < h) {
        if (!m[sy * w + sx] || groundY - (y0 + sy) <= 0) { sy++; continue; }
        const start = sy;
        while (sy < h && m[sy * w + sx] && groundY - (y0 + sy) > 0) sy++;
        const top = groundY - (y0 + start), bot = Math.max(0, groundY - (y0 + sy));
        const wx = x0 + sx, bx = wx + 0.5;
        const fade = (px, py) => {
          const dx = px - bx, dy = py - groundY;
          return 1 - (1 - fadeTo) * Math.min(1, Math.sqrt(dx * dx + dy * dy) / fadeLen);
        };
        fillConvex(mask, mw, mh, [
          this.project(light, wx, groundY, bot), this.project(light, wx + 1, groundY, bot),
          this.project(light, wx + 1, groundY, top), this.project(light, wx, groundY, top),
        ], ox, oy, fade);
      }
    }
  }

  // Bake light textures: for each light a shadowed (floor) and an unshadowed (objects) canvas.
  build() {
    const { W, H, cfg } = this;
    const levels = cfg.levels;
    for (const L of this.lights) {
      const sh = cfg.shadow * (L.shadow ?? 1);
      const R = L.radius, size = 2 * R + 1;
      const ox = Math.round(L.x) - R, oy = Math.round(L.y) - R;
      const mask = new Float32Array(size * size);
      for (const o of this.occluders) {
        if (o.owner === L.owner && L.owner != null) continue;
        const cx = o.box ? (o.x0 + o.x1) / 2 : o.x0 + o.w / 2, cy = o.box ? o.y1 : o.groundY;
        if (Math.hypot(cx - L.x, cy - L.y) > R + 40) continue;
        this.castShadow(mask, size, size, ox, oy, L, o);
      }
      for (const o of this.walls) this.castShadow(mask, size, size, ox, oy, L, o);
      blur(mask, size, size, cfg.blur ?? 1, 2);
      for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
        const wx = ox + x, wy = oy + y;
        if (wx >= 0 && wy >= 0 && wx < W && wy < H && this.wallMask[wy * W + wx]) mask[y * size + x] = 0;
      }
      const [lit, litCtx] = canvas(size, size), [raw, rawCtx] = canvas(size, size);
      const a = litCtx.createImageData(size, size), b = rawCtx.createImageData(size, size);
      const col = rgb(L.color);
      for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
        const d = Math.hypot(x - R, (y - R) * 1.15) / R;  // slightly squashed: ground plane in 3/4 view
        if (d >= 1) continue;
        const f = Math.pow(1 - d, 1.5) * L.intensity;
        const q = band(f, levels);
        const qs = band(f * (1 - sh * mask[y * size + x]), levels);
        const i = (y * size + x) * 4;
        for (let k = 0; k < 3; k++) { a.data[i + k] = col[k] * qs; b.data[i + k] = col[k] * q; }
        a.data[i + 3] = b.data[i + 3] = 255;
      }
      litCtx.putImageData(a, 0, 0); rawCtx.putImageData(b, 0, 0);
      Object.assign(L, { lit, raw, ox, oy });
    }
    // moon: uniform light over the whole map with its shadows cut out
    const m = new Float32Array(W * H);
    for (const o of this.occluders) this.castShadow(m, W, H, 0, 0, null, o);
    for (const o of this.walls) this.castShadow(m, W, H, 0, 0, null, o);
    blur(m, W, H, cfg.blur ?? 1, 2);
    for (let i = 0; i < W * H; i++) if (this.wallMask[i]) m[i] = 0;
    const [moonLit, mctx] = canvas(W, H);
    const img = mctx.createImageData(W, H), mc = rgb(cfg.moon.color);
    const lv = cfg.levels;
    for (let i = 0; i < W * H; i++) {
      const f = band(1 - cfg.moon.shadow * m[i], lv);
      for (let k = 0; k < 3; k++) img.data[i * 4 + k] = mc[k] * f;
      img.data[i * 4 + 3] = 255;
    }
    mctx.putImageData(img, 0, 0);
    this.moonLit = moonLit;
    // Addition of nonnegative byte channels is associative, including saturation.
    // Bake the moon and constant lights together; flickering lights still add separately.
    const steady = this.lights.filter(L => !L.flicker);
    this.flickering = this.lights.filter(L => L.flicker);
    const sx = Math.min(0, ...steady.map(L => L.ox)), sy = Math.min(0, ...steady.map(L => L.oy));
    const sw = Math.max(W, ...steady.map(L => L.ox + L.lit.width)) - sx;
    const sh = Math.max(H, ...steady.map(L => L.oy + L.lit.height)) - sy;
    this.steady = { x: sx, y: sy };
    for (const which of ["lit", "raw"]) {
      const [c, g] = canvas(sw, sh);
      g.globalCompositeOperation = "lighter";
      g.drawImage(which === "lit" ? this.moonLit : this.moonRaw(), -sx, -sy);
      for (const L of steady) g.drawImage(L[which], L.ox - sx, L.oy - sy);
      this.steady[which] = c;
    }
    // contact shadows: darken just around each footprint (multiply layer)
    const [ao, actx] = canvas(W, H);
    actx.fillStyle = "#fff"; actx.fillRect(0, 0, W, H);
    for (const o of this.occluders) {
      if (o.box) continue;
      const fy = o.groundY - 1, fw = o.fw;
      actx.fillStyle = "#909090"; actx.fillRect(Math.round(o.cx - fw / 2) - 1, fy - 1, fw + 2, o.y0 + o.h - fy + 2);
      actx.fillStyle = "#505050"; actx.fillRect(Math.round(o.cx - fw / 2), fy, fw, o.y0 + o.h - fy + 1);
    }
    this.ao = ao;
  }

  // Light buffer for the view: direct light (moon + point lights), optionally occluded by
  // `occlude(ctx)` (multiply layers: contact shadows, moving shadows), THEN + ambient.
  // Occlusion only ever removes direct light, so any number of overlapping shadows can at
  // most reach "no direct light" = ambient only, never darker.
  lightMap(ctx, camX, camY, VW, VH, which, t, occlude = null, dynamic = null) {
    ctx.globalCompositeOperation = "source-over";
    ctx.globalAlpha = 1;
    ctx.fillStyle = "#000"; ctx.fillRect(0, 0, VW, VH);
    ctx.globalCompositeOperation = "lighter";
    ctx.drawImage(this.steady[which], this.steady.x - camX, this.steady.y - camY);
    for (const L of this.flickering) {
      const k = L.flicker(t);
      if (k <= 0) continue;
      ctx.globalAlpha = Math.min(1, k);
      ctx.drawImage(L[which], L.ox - camX, L.oy - camY);
    }
    ctx.globalAlpha = 1;
    if (dynamic) this.drawDynamic(ctx, dynamic, which);
    if (occlude) { ctx.globalCompositeOperation = "multiply"; occlude(ctx); }
    ctx.globalCompositeOperation = "lighter";
    ctx.fillStyle = this.cfg.ambient; ctx.fillRect(0, 0, VW, VH);
    ctx.globalCompositeOperation = "source-over";
  }

  // Black pixels outside the current light bounds add nothing, even for bloom.
  drawDynamic(ctx, dynamic, which) {
    const { x, y, w, h } = dynamic;
    if (w && h) ctx.drawImage(dynamic[which], x, y, w, h, x, y, w, h);
  }

  moonRaw() {
    if (!this._moonRaw) {
      const [c, x] = canvas(this.W, this.H);
      x.fillStyle = this.cfg.moon.color; x.fillRect(0, 0, this.W, this.H);
      this._moonRaw = c;
    }
    return this._moonRaw;
  }

  // Per-frame shadow of a moving occluder (the hero): a multiply layer over the DIRECT light
  // (call from lightMap's occlude step). Overlaps multiply down to 0 = no direct light.
  dynamicShadow(ctx, o, camX, camY, t) {
    const R = 72, size = 2 * R, ox = Math.round(o.x0 + o.w / 2) - R, oy = Math.round(o.groundY) - R;
    if (!this._heroShadow) {
      const [c, x] = canvas(size, size);
      this._heroShadow = { c, x, img: x.createImageData(size, size),
        shade: new Float32Array(size * size), mask: new Float32Array(size * size),
        crop: new Float32Array(size * size), tmp: new Float32Array(size * size) };
    }
    const { c, x, img, shade, mask: m, crop, tmp } = this._heroShadow;
    shade.fill(1);
    const apply = (light, strength) => {
      m.fill(0);
      this.castShadow(m, size, size, ox, oy, light, o);
      // The hero occupies a small part of this buffer. Crop the nonzero mask
      // with a two-pass blur halo, preserving the original buffer's edge clamp.
      let left = size, right = 0, top = size, bottom = 0;
      for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
        if (!m[y * size + x]) continue;
        left = Math.min(left, x); right = Math.max(right, x + 1);
        top = Math.min(top, y); bottom = y + 1;
      }
      if (left >= right) return;
      const r = this.cfg.blur ?? 1, halo = 2 * r;
      left = Math.max(0, left - halo); right = Math.min(size, right + halo);
      top = Math.max(0, top - halo); bottom = Math.min(size, bottom + halo);
      const w = right - left, h = bottom - top;
      for (let y = 0; y < h; y++) crop.set(m.subarray((top + y) * size + left, (top + y) * size + right), y * w);
      blur(crop, w, h, r, 2, tmp);
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        const v = crop[y * w + x];
        if (v > 0.01) shade[(top + y) * size + left + x] *= 1 - strength * v;
      }
    };
    apply(null, this.cfg.moon.shadow * 0.45);
    for (const L of this.lights) {
      const d = Math.hypot(o.x0 + o.w / 2 - L.x, o.groundY - L.y) / L.radius;
      if (d >= 1) continue;
      apply(L, 0.75 * (L.shadow ?? 1) * Math.pow(1 - d, 1.2) * L.intensity * (L.flicker ? L.flicker(t) : 1));
    }
    for (let i = 0; i < shade.length; i++) {
      // flat bands like the light maps: soft edges become a few clean steps
      const v = band(shade[i], this.cfg.levels);
      img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = 255 * v;
      img.data[i * 4 + 3] = 255;
    }
    x.putImageData(img, 0, 0);
    ctx.drawImage(c, ox - camX, oy - camY);
  }

  // Moving lights (e.g. a flyover), recomputed every frame for the visible area only.
  // lights: [{ type: "spot", x, y, h, tx, ty, inner, outer, range, color, intensity, shadows }
  //          | { type: "point", x, y, h, radius, color, intensity, shadows }]
  // Returns { lit, raw } view-sized canvases to add into lightMap (lit has shadows cut out).
  dynamicLights(lights, occluders, camX, camY, VW, VH) {
    if (!this._dl || this._dl.lit.width !== VW || this._dl.lit.height !== VH) {
      const [lit, a] = canvas(VW, VH), [raw, b] = canvas(VW, VH);
      this._dl = { lit, raw, a, b, ia: a.createImageData(VW, VH), ib: b.createImageData(VW, VH),
        accLit: new Float32Array(VW * VH * 3), accRaw: new Float32Array(VW * VH * 3),
        mask: new Float32Array(VW * VH), tmp: new Float32Array(VW * VH),
        rows: new Int32Array(VH * 2), active: new Int32Array(VH * 2),
        x: 0, y: 0, w: 0, h: 0 };
      const D = this._dl;
      for (let i = 3; i < D.ia.data.length; i += 4) D.ia.data[i] = D.ib.data[i] = 255;
      D.pixelsLit = new Uint32Array(D.ia.data.buffer);
      D.pixelsRaw = new Uint32Array(D.ib.data.buffer);
      D.black = D.pixelsLit[0]; // native-endian opaque black
      a.putImageData(D.ia, 0, 0); b.putImageData(D.ib, 0, 0);
    }
    const D = this._dl, levels = this.cfg.levels;
    if (D.levels !== levels) {
      D.levels = levels;
      D.bands = new Uint8ClampedArray(levels + 1);
      for (let i = 0; i <= levels; i++) D.bands[i] = 255 * (i / levels);
    }
    // Retire last frame's spans before accumulating this frame. Keep the image
    // opaque black elsewhere, and upload the old/new bounding union to erase exits.
    let dirtyX0 = D.w ? D.x : VW, dirtyY0 = D.h ? D.y : VH;
    let dirtyX1 = D.w ? D.x + D.w : 0, dirtyY1 = D.h ? D.y + D.h : 0;
    for (let y = 0; y < VH; y++) {
      const lo = y * VW + D.active[y * 2], hi = y * VW + D.active[y * 2 + 1];
      D.accLit.fill(0, lo * 3, hi * 3); D.accRaw.fill(0, lo * 3, hi * 3);
      D.pixelsLit.fill(D.black, lo, hi); D.pixelsRaw.fill(D.black, lo, hi);
      D.active[y * 2] = VW; D.active[y * 2 + 1] = 0;
    }
    let activeX0 = VW, activeY0 = VH, activeX1 = 0, activeY1 = 0;
    for (const L of lights) {
      const col = rgb(L.color).map(v => v / 255);
      // bounding box of the lit ground area, clipped to the view
      // spots: attenuation reaches exactly 0 at 2.2 * range from the aim point, so the box
      // never clips a lit pixel (no hard edges)
      const reach = L.type === "spot" ? L.range * 2.2 : L.radius;
      const cx = L.type === "spot" ? L.tx : L.x, cy = L.type === "spot" ? L.ty : L.y;
      let x0 = Math.max(0, Math.floor(cx - reach - camX)), x1 = Math.min(VW, Math.ceil(cx + reach - camX));
      let y0 = Math.max(0, Math.floor(cy - reach - camY)), y1 = Math.min(VH, Math.ceil(cy + reach - camY));
      if (x0 >= x1 || y0 >= y1) continue;
      let ax = 0, ay = 0, az = 0, cosIn = 0, cosOut = 0;
      if (L.type === "spot") {
        ax = L.tx - L.x; ay = L.ty - L.y; az = -L.h;
        const n = Math.hypot(ax, ay, az); ax /= n; ay /= n; az /= n;
        cosIn = Math.cos(L.inner); cosOut = Math.cos(L.outer);
      }
      // Intersect each scanline with the attenuation ellipse/circle and cone.
      // These spans are conservative; the original falloff test still decides
      // whether a pixel contributes. Near-horizontal cones use the circle alone.
      let left = x1, right = x0, top = y1, bottom = y0;
      for (let y = y0; y < y1; y++) {
        const wy = y + camY + 0.5, dy = (wy - cy) * (L.type === "spot" ? 1 : 1.15);
        const rr = reach * reach - dy * dy;
        let lo = x1, hi = x0;
        if (rr > 0) {
          const dx = Math.sqrt(rr);
          lo = Math.max(x0, Math.floor(cx - dx - camX));
          hi = Math.min(x1, Math.ceil(cx + dx - camX));
          const a = ax * ax - cosOut * cosOut;
          if (L.type === "spot" && a < -1e-9 && cosOut > 0) {
            // (axis dot ray)^2 > cos(outer)^2 * |ray|^2 is a
            // quadratic in ray.x. A negative leading term bounds one interval.
            const vy = wy - L.y, b = ay * vy - az * L.h;
            const q = ax * b, c = b * b - cosOut * cosOut * (vy * vy + L.h * L.h);
            const disc = q * q - a * c;
            if (disc <= 0) hi = lo;
            else {
              const d = Math.sqrt(disc);
              lo = Math.max(lo, Math.floor(L.x + (-q + d) / a - camX));
              hi = Math.min(hi, Math.ceil(L.x + (-q - d) / a - camX));
            }
          }
        }
        D.rows[y * 2] = lo; D.rows[y * 2 + 1] = hi;
        if (lo < hi) {
          D.active[y * 2] = Math.min(D.active[y * 2], lo);
          D.active[y * 2 + 1] = Math.max(D.active[y * 2 + 1], hi);
          left = Math.min(left, lo); right = Math.max(right, hi);
          top = Math.min(top, y); bottom = y + 1;
        }
      }
      if (left >= right) continue;
      activeX0 = Math.min(activeX0, left); activeX1 = Math.max(activeX1, right);
      activeY0 = Math.min(activeY0, top); activeY1 = Math.max(activeY1, bottom);
      // Two blur passes can pull shadows in from 2*r pixels beyond the lit area.
      // Retain that halo, clipped to the old bounds so edge clamping stays identical.
      const halo = 2 * (this.cfg.blur ?? 1);
      x0 = Math.max(x0, left - halo); x1 = Math.min(x1, right + halo);
      y0 = Math.max(y0, top - halo); y1 = Math.min(y1, bottom + halo);
      const bw = x1 - x0, bh = y1 - y0;
      let mask = null;
      if (L.shadows) {
        mask = D.mask;
        mask.fill(0, 0, bw * bh);
        const light = { x: L.x, y: L.y, h: L.h };
        for (const o of occluders) this.castShadow(mask, bw, bh, x0 + camX, y0 + camY, light, o);
        blur(mask, bw, bh, this.cfg.blur ?? 1, 2, D.tmp);
      }
      for (let sy = top; sy < bottom; sy++) for (let sx = D.rows[sy * 2]; sx < D.rows[sy * 2 + 1]; sx++) {
        const x = sx - x0, y = sy - y0;
        const wx = x0 + camX + x + 0.5, wy = y0 + camY + y + 0.5;
        let f;
        if (L.type === "spot") {
          const vx = wx - L.x, vy = wy - L.y, vz = -L.h, d = Math.sqrt(vx * vx + vy * vy + vz * vz);
          const c = (vx * ax + vy * ay + vz * az) / d;
          if (c <= cosOut) continue;
          const k = Math.min(1, (c - cosOut) / (cosIn - cosOut));
          const spot = k * k * (3 - 2 * k);  // smoothstep: soft beam edge
          const dx = wx - L.tx, dy = wy - L.ty, dr2 = (dx * dx + dy * dy) / (reach * reach);
          if (dr2 >= 1) continue;
          f = spot * L.intensity * (1 - dr2) / (1 + dr2 * 2.2 * 2.2 * 2);
        } else {
          const dx = wx - L.x, dy = (wy - L.y) * 1.15;
          const d = Math.sqrt(dx * dx + dy * dy) / L.radius;
          if (d >= 1) continue;
          const v = 1 - d;
          f = v * Math.sqrt(v) * L.intensity;
        }
        const i = ((y0 + y) * VW + x0 + x) * 3;
        let fs = f;
        if (mask) {
          const mx = x0 + camX + x, my = y0 + camY + y;
          const wall = mx >= 0 && my >= 0 && mx < this.W && my < this.H && this.wallMask[my * this.W + mx];
          if (!wall) fs *= 1 - this.cfg.shadow * mask[y * bw + x];
        }
        D.accRaw[i] += f * col[0]; D.accLit[i] += fs * col[0];
        D.accRaw[i + 1] += f * col[1]; D.accLit[i + 1] += fs * col[1];
        D.accRaw[i + 2] += f * col[2]; D.accLit[i + 2] += fs * col[2];
      }
    }
    // flat bands per channel, like the baked lights
    writeLightBands(D, VW, levels, activeY0, activeY1);
    D.x = activeX0; D.y = activeY0;
    D.w = Math.max(0, activeX1 - activeX0); D.h = Math.max(0, activeY1 - activeY0);
    dirtyX0 = Math.min(dirtyX0, activeX0); dirtyX1 = Math.max(dirtyX1, activeX1);
    dirtyY0 = Math.min(dirtyY0, activeY0); dirtyY1 = Math.max(dirtyY1, activeY1);
    if (dirtyX0 < dirtyX1 && dirtyY0 < dirtyY1) {
      D.a.putImageData(D.ia, 0, 0, dirtyX0, dirtyY0, dirtyX1 - dirtyX0, dirtyY1 - dirtyY0);
      D.b.putImageData(D.ib, 0, 0, dirtyX0, dirtyY0, dirtyX1 - dirtyX0, dirtyY1 - dirtyY0);
    }
    return D;
  }
}
