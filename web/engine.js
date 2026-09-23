// Minimal 2D engine: tilemap, 8-direction character controller, sprite-sheet animation.
// Characters come from data/characters/<name>/sheet.{png,json} (written by `just build`).

const VIEW_W = 400, VIEW_H = 240;
const BASE = "data/characters/";

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
function fit() {
  const s = Math.max(1, Math.floor(Math.min((innerWidth - 20) / VIEW_W, (innerHeight - 80) / VIEW_H)));
  canvas.width = VIEW_W; canvas.height = VIEW_H;
  canvas.style.width = VIEW_W * s + "px"; canvas.style.height = VIEW_H * s + "px";
  ctx.imageSmoothingEnabled = false;
}
addEventListener("resize", fit); fit();

// ------------------------------------------------------------------ assets
async function loadCharacter(name) {
  const meta = await (await fetch(BASE + name + "/sheet.json", { cache: "no-store" })).json();
  const img = new Image();
  img.src = BASE + name + "/sheet.png?" + Date.now();
  await img.decode();
  return { name, meta, img };
}

// ------------------------------------------------------------------ level
// Tiles and props come from data/props/atlas.{png,json} (written by `just props`).
import { TILE, LEGEND, SLABS, SOLID_TILES, MAP, PROPS, DECALS, LIGHTING, FLYOVER } from "./rooftop.js";
import { Lighting, alphaMask, setDitherNoise } from "./lighting.js";

const MAP_W = MAP[0].length * TILE, MAP_H = MAP.length * TILE;
let atlas, atlasImg, emissiveImg, mapCanvas, emissiveMap, solids = [], props = [], animDecals = [];
let lighting, lightingOn = true, hud = true;

// Each placed prop gets its own phase so identical props don't animate in lockstep.
function instance(name, x, y) {
  const s = atlas.sprites[name];
  const total = s.anim ? s.anim.reduce((a, b) => a + b, 0) : 0;
  return { name, x, y, s, total, phase: hash(x, y) * total };
}

// Current frame index of an animated prop at time t (ms).
// Capture-only (README loop): with loopMs set, every prop animation runs a whole number of
// cycles per loop (each cycle stretched a few percent), so the loop has no seam.
let loopMs = 0;
function frameIndex(p, t) {
  if (!p.s.anim) return 0;
  if (loopMs) t = (t % loopMs) * Math.max(1, Math.round(loopMs / p.total)) * p.total / loopMs;
  let k = (t + p.phase) % p.total;
  for (let i = 0; i < p.s.anim.length; i++) { if (k < p.s.anim[i]) return i; k -= p.s.anim[i]; }
  return 0;
}

// Big slabs: rank the aligned 2x2 blocks of plain floor by hash, turn the first
// SLABS.chance of them into slabs, and deal the slab sets out in turn so each one is used.
let slabs = null;
function slabTile(tx, ty) {
  if (!slabs) {
    const blocks = [];
    for (let by = 0; by + 1 < MAP.length; by += 2) for (let bx = 0; bx + 1 < MAP[0].length; bx += 2) {
      if ([0, 1].every(dy => [0, 1].every(dx => MAP[by + dy][bx + dx] === "."))) blocks.push([bx, by]);
    }
    blocks.sort((p, q) => hash(p[0] * 31 + 7, p[1] * 17 + 3) - hash(q[0] * 31 + 7, q[1] * 17 + 3));
    slabs = new Map(blocks.slice(0, Math.round(blocks.length * SLABS.chance))
      .map(([bx, by], i) => [`${bx},${by}`, SLABS.sets[i % SLABS.sets.length]]));
  }
  const bx = tx - (tx & 1), by = ty - (ty & 1), set = slabs.get(`${bx},${by}`);
  return set ? `${set}_${ty === by ? "t" : "b"}${tx === bx ? "l" : "r"}` : null;
}

// Integer hash of a cell -> [0, 1). Math.imul keeps the mixing in 32 bits (plain float
// multiplies lost the low bits, and the result never reached 0.5).
function hash(x, y) {
  let h = Math.imul(x, 374761393) ^ Math.imul(y, 668265263);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

async function loadLevel() {
  atlas = await (await fetch("data/props/atlas.json", { cache: "no-store" })).json();
  atlasImg = new Image();
  atlasImg.src = "data/props/atlas.png?" + Date.now();
  emissiveImg = new Image();
  emissiveImg.src = "data/props/atlas_emissive.png?" + Date.now();
  await Promise.all([atlasImg.decode(), emissiveImg.decode()]);
  emissiveMap = document.createElement("canvas");
  emissiveMap.width = MAP_W; emissiveMap.height = MAP_H;
  const em = emissiveMap.getContext("2d");
  // bake floor tiles + decals into one canvas
  mapCanvas = document.createElement("canvas");
  mapCanvas.width = MAP_W; mapCanvas.height = MAP_H;
  const m = mapCanvas.getContext("2d");
  MAP.forEach((row, ty) => [...row].forEach((ch, tx) => {
    const opts = LEGEND[ch];
    const t = atlas.tiles[slabTile(tx, ty) ?? opts[Math.floor(hash(tx, ty) * opts.length)]];
    m.drawImage(atlasImg, t.x, t.y, t.w, t.h, tx * TILE, ty * TILE, TILE, TILE);
    em.drawImage(emissiveImg, t.x, t.y, t.w, t.h, tx * TILE, ty * TILE, TILE, TILE);
  }));
  // static decals are baked into the floor; animated ones are drawn every frame
  for (const [name, x, y] of DECALS) {
    const s = atlas.sprites[name];
    if (s.anim) { animDecals.push(instance(name, x, y)); continue; }
    m.drawImage(atlasImg, s.x, s.y, s.w, s.h, Math.round(x - s.w / 2), Math.round(y - s.h), s.w, s.h);
    em.drawImage(emissiveImg, s.x, s.y, s.w, s.h, Math.round(x - s.w / 2), Math.round(y - s.h), s.w, s.h);
  }
  // standing props: drawn y-sorted with the character; base footprint blocks movement
  props = PROPS.map(([name, x, y]) => instance(name, x, y));
  solids = props.filter(p => p.s.kind === "solid")
    .map(p => ({ x0: p.x - p.s.w / 2 + 2, x1: p.x + p.s.w / 2 - 2, y0: p.y - p.s.base, y1: p.y }));
  buildLighting();
  // Prepare every animation/direction variant before the first rendered frame.
  for (const car of FLYOVER.cars) for (const dir of [-1, 1]) {
    const s = atlas.sprites[car];
    for (const f of s.frames) {
      flyerSprite(car, dir, s, f, false);
      flyerSprite(car, dir, s, f, true);
      flyerShadowSprite(car, dir, s, f);
    }
  }
}

// Blue-noise threshold map (tools/bluenoise.py) that dithers the lighting's band edges.
async function loadDitherNoise() {
  const img = new Image();
  img.src = "bluenoise.png";
  await img.decode();
  const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
  const g = c.getContext("2d"); g.drawImage(img, 0, 0);
  const px = g.getImageData(0, 0, img.width, img.height).data, map = new Float32Array(img.width * img.height);
  for (let i = 0; i < map.length; i++) map[i] = (px[i * 4] + 0.5) / 256;
  setDitherNoise(map, LIGHTING.dither ?? 0);
}

function buildLighting() {
  const flicker = p => p.s.glow_anim ? t => p.s.glow_anim[frameIndex(p, t)] : null;
  const lights = [...props, ...animDecals].filter(p => p.s.glow).map(p => ({
    x: p.x, y: p.y + 2, h: p.s.kind === "decal" ? 2 : Math.max(6, Math.round(p.s.h * 0.55)),
    color: p.s.glow, radius: p.name === "fire_barrel" ? 96 : Math.round(56 + p.s.w * 1.8),
    intensity: p.name === "fire_barrel" ? 1.1 : 0.9,
    owner: p, flicker: flicker(p),
  }));
  MAP.forEach((row, ty) => [...row].forEach((ch, tx) => {
    if ("<-=>".includes(ch))
      lights.push({ x: tx * TILE + 8, y: ty * TILE + 9, h: 2, color: "#e8358c", radius: 34, intensity: 0.55, shadow: 0.3, maxShadow: 20 });
    if (ch === "N")
      lights.push({ x: tx * TILE + 8, y: ty * TILE + 20, h: 10, color: "#3ff0ff", radius: 64, intensity: 0.75 });
  }));
  const occluders = props.filter(p => p.s.kind === "solid").map(p => ({
    x0: Math.round(p.x - p.s.w / 2), y0: Math.round(p.y - p.s.h), w: p.s.w, h: p.s.h,
    m: alphaMask(atlasImg, p.s.x, p.s.y, p.s.w, p.s.h),
    groundY: p.y - Math.max(1, Math.round(p.s.base / 2)), owner: p, cx: p.x, fw: p.s.w - 2,
  }));
  const walls = [];
  MAP.forEach((row, ty) => [...row].forEach((ch, tx) => {
    if (SOLID_TILES.has(ch)) walls.push({ box: true, x0: tx * TILE, y0: ty * TILE, x1: tx * TILE + TILE, y1: ty * TILE + TILE, h: 14 });
  }));
  lighting = new Lighting({ W: MAP_W, H: MAP_H, cfg: LIGHTING, lights, occluders, walls });
  const t0 = performance.now();
  lighting.build();
  console.log(`lighting: ${lights.length} lights, ${occluders.length} occluders, baked in ${Math.round(performance.now() - t0)} ms`);
}

function drawProp(p, camX, camY, t, g = ctx, img = atlasImg) {
  const s = p.s, f = s.frames[frameIndex(p, t)];
  g.drawImage(img, f.x, f.y, s.w, s.h, Math.round(p.x - s.w / 2 - camX), Math.round(p.y - s.h - camY), s.w, s.h);
}

function drawGlows(camX, camY, t) {
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (const p of props) {
    if (!p.s.glow) continue;
    const flick = p.s.glow_anim ? p.s.glow_anim[frameIndex(p, t)] : 1;
    const cx = p.x - camX, cy = p.y - p.s.h * 0.6 - camY, r = 26 + p.s.w * 0.6;
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    const a = lightingOn ? 26 : 56;  // with real lighting the halo is only a soft bloom
    g.addColorStop(0, p.s.glow + Math.round(Math.min(255, a * flick)).toString(16).padStart(2, "0"));
    g.addColorStop(1, p.s.glow + "00");
    ctx.fillStyle = g;
    ctx.fillRect(cx - r, cy - r, r * 2, r * 2);
  }
  ctx.restore();
}

// ------------------------------------------------------------------ input
const keys = new Set(), pressed = new Set();
addEventListener("keydown", e => {
  if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " ", "Tab"].includes(e.key)) e.preventDefault();
  const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
  if (!keys.has(k)) pressed.add(k);
  keys.add(k);
});
addEventListener("keyup", e => keys.delete(e.key.length === 1 ? e.key.toLowerCase() : e.key));
const down = (...ks) => ks.some(k => keys.has(k));
const hit = k => pressed.has(k);

// ------------------------------------------------------------------ character
// 8 compass directions -> sheet facings (left facings are separate rows, not flips).
const FACING = {
  "0,1": "down", "1,1": "down_side", "1,0": "side", "1,-1": "up_side",
  "0,-1": "up", "-1,-1": "up_side_l", "-1,0": "side_l", "-1,1": "down_side_l",
};
const ONE_SHOT = new Set(["jump", "attack", "interact", "rotate"]);

const hero = { x: 216, y: 132, facing: "down", anim: "idle", frame: 0, t: 0 };
let chars = [], ci = 0, gallery = false, galleryT = 0;

function play(anim) {
  if (hero.anim === anim) return;
  hero.anim = anim; hero.frame = 0; hero.t = 0;
}

function frames(c, anim, facing) {
  const a = c.meta.anims[anim];
  return a[facing] || a.all;
}

function collide(x, y) {
  // feet hitbox: 8x4 px around the ground point
  for (const [dx, dy] of [[-4, -3], [3, -3], [-4, 0], [3, 0]]) {
    const t = MAP[Math.floor((y + dy) / TILE)]?.[Math.floor((x + dx) / TILE)];
    if (t === undefined || SOLID_TILES.has(t)) return true;
  }
  return solids.some(b => x + 4 > b.x0 && x - 4 < b.x1 && y > b.y0 && y - 3 < b.y1);
}

// ------------------------------------------------------------------ flyover
// World-space path across the current view, starting/ending FLYOVER.margin outside it.
// Cars are independent: each finishes its own pass; new ones spawn on their own timer.
let flyers = [], nextFly = 2000, autoFly = true;
function spawnFlyer(camX, camY) {
  const dir = Math.random() < 0.5 ? 1 : -1, m = FLYOVER.margin;
  const y = camY + 20 + Math.random() * (VIEW_H - 40);
  const x = dir > 0 ? camX - m : camX + VIEW_W + m;
  const car = FLYOVER.cars[Math.floor(Math.random() * FLYOVER.cars.length)];
  flyers.push({ x, y, dir, endX: dir > 0 ? camX + VIEW_W + m : camX - m, car, t0: performance.now() });
}
function updateFlyers(dt) {
  const camX = Math.max(0, Math.min(MAP_W - VIEW_W, hero.x - VIEW_W / 2));
  const camY = Math.max(0, Math.min(MAP_H - VIEW_H, hero.y - VIEW_H / 2));
  if (hit("f")) spawnFlyer(camX, camY);
  if (autoFly) nextFly -= dt;
  if (nextFly <= 0) {
    spawnFlyer(camX, camY);
    const [a, b] = FLYOVER.every;
    nextFly = a + Math.random() * (b - a);
  }
  for (const f of flyers) f.x += f.dir * FLYOVER.speed * dt / 1000;
  flyers = flyers.filter(f => (f.x - f.endX) * f.dir <= 0);
}
function flyerLights() {
  const F = FLYOVER, h = F.height, out = [];
  for (const { x, y, dir, car } of flyers) {
    const s = atlas.sprites[car], nose = x + dir * s.w * 0.45, tail = x - dir * s.w * 0.45;
    out.push(
      { type: "spot", x: nose, y, h, tx: nose + dir * F.ahead, ty: y + 6, shadows: true, ...F.headlight },
      { type: "point", x: tail, y: y - F.tail.spread, h, shadows: false, ...F.tail },
      { type: "point", x: tail, y: y + F.tail.spread, h, shadows: false, ...F.tail },
      { type: "point", x, y, h, shadows: false, ...F.under },
    );
  }
  return out;
}

// A car flies FLYOVER.height px above its ground point, so on screen it is drawn that much
// higher. It is above the roof: lit by moon + ambient only, lamp pixels drawn full-bright.
const [carC, carCtx] = (() => { const c = document.createElement("canvas"); c.width = 160; c.height = 80;
  const g = c.getContext("2d"); g.imageSmoothingEnabled = false; return [c, g]; })();
const carSprites = new Map(), carShadows = new Map();
function copyCanvas(source, w, h) {
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  c.getContext("2d").drawImage(source, 0, 0);
  return c;
}
function carFrame(fl, t) {
  const s = atlas.sprites[fl.car];
  return { s, f: s.frames[Math.floor(t / s.anim[0]) % s.frames.length] };
}
function drawFlyer(fl, camX, camY, t, lit) {
  const { s, f } = carFrame(fl, t);
  const bob = Math.round(Math.sin((t - fl.t0) / 260) * FLYOVER.bob);
  const sx = Math.round(fl.x - camX - s.w / 2), sy = Math.round(fl.y - FLYOVER.height - s.h - camY + bob);
  ctx.drawImage(flyerSprite(fl.car, fl.dir, s, f, lit), sx, sy);
}
function flyerSprite(car, dir, s, f, lit) {
  const key = `${car}|${f.x}|${f.y}|${dir}|${!!lit}`;
  if (carSprites.has(key)) return carSprites.get(key);
  carCtx.clearRect(0, 0, carC.width, carC.height);
  carCtx.save();
  if (dir < 0) { carCtx.translate(s.w, 0); carCtx.scale(-1, 1); }
  carCtx.drawImage(atlasImg, f.x, f.y, s.w, s.h, 0, 0, s.w, s.h);
  if (lit) {  // moon + ambient light, then restore the car's alpha, then lamps unlit
    carCtx.globalCompositeOperation = "multiply";
    carCtx.fillStyle = LIGHTING.carLight; carCtx.fillRect(0, 0, s.w, s.h);
    carCtx.globalCompositeOperation = "destination-in";
    carCtx.drawImage(atlasImg, f.x, f.y, s.w, s.h, 0, 0, s.w, s.h);
    carCtx.globalCompositeOperation = "source-over";
    carCtx.drawImage(emissiveImg, f.x, f.y, s.w, s.h, 0, 0, s.w, s.h);
  }
  carCtx.restore();
  const sprite = copyCanvas(carC, s.w, s.h);
  carSprites.set(key, sprite);
  return sprite;
}
// Soft moon shadow of a car on the roof (an occluder of direct light only).
const [shC, shCtx] = (() => { const c = document.createElement("canvas"); c.width = 180; c.height = 100;
  return [c, c.getContext("2d")]; })();
function flyerShadow(fl, g, camX, camY, t) {
  const { s, f } = carFrame(fl, t), M = LIGHTING.moon, k = FLYOVER.height * M.length;
  g.drawImage(flyerShadowSprite(fl.car, fl.dir, s, f), Math.round(fl.x + M.dir[0] * k - s.w / 2 - 10 - camX), Math.round(fl.y + M.dir[1] * k - s.h * 0.4 - 20 - camY));
}
function flyerShadowSprite(car, dir, s, f) {
  const key = `${car}|${f.x}|${f.y}|${dir}`;
  if (carShadows.has(key)) return carShadows.get(key);
  shCtx.clearRect(0, 0, shC.width, shC.height);
  shCtx.filter = "blur(2px)";
  shCtx.save();
  if (dir < 0) { shCtx.translate(10 + s.w, 0); shCtx.scale(-1, 1); shCtx.translate(-10, 0); }
  // footprint: the silhouette squashed vertically (seen from above), darkened
  shCtx.drawImage(atlasImg, f.x, f.y, s.w, s.h, 10, 20, s.w, Math.round(s.h * 0.55));
  shCtx.restore();
  shCtx.filter = "none";
  shCtx.globalCompositeOperation = "source-in";
  shCtx.fillStyle = "#383838"; shCtx.fillRect(0, 0, shC.width, shC.height);
  shCtx.globalCompositeOperation = "destination-over";
  shCtx.fillStyle = "#fff"; shCtx.fillRect(0, 0, shC.width, shC.height);
  shCtx.globalCompositeOperation = "source-over";
  const shadow = copyCanvas(shC, shC.width, shC.height);
  carShadows.set(key, shadow);
  return shadow;
}

function update(dt) {
  updateFlyers(dt);
  const c = chars[ci];
  if (hit("c")) { ci = (ci + 1) % chars.length; }
  if (hit("v")) gallery = !gallery;
  if (hit("l")) lightingOn = !lightingOn;
  if (hit("-")) setDarkness(darkness - 0.1);
  if (hit("=") || hit("+")) setDarkness(darkness + 0.1);
  const busy = ONE_SHOT.has(hero.anim) && hero.anim !== "jump";
  if (!busy) {
    if (hit(" ")) play("jump");
    else if (hit("j")) play("attack");
    else if (hit("e")) play("interact");
    else if (hit("r")) play("rotate");
  }
  let mx = (down("d", "ArrowRight") ? 1 : 0) - (down("a", "ArrowLeft") ? 1 : 0);
  let my = (down("s", "ArrowDown") ? 1 : 0) - (down("w", "ArrowUp") ? 1 : 0);
  const moving = (mx || my) && !ONE_SHOT.has(hero.anim) || (hero.anim === "jump" && (mx || my));
  if (mx || my) {
    if (!ONE_SHOT.has(hero.anim)) hero.facing = FACING[`${mx},${my}`];
  }
  if (moving) {
    const run = down("Shift");
    const speed = (run ? 90 : 48) * dt / 1000;
    const len = Math.hypot(mx, my);
    const nx = hero.x + mx / len * speed, ny = hero.y + my / len * speed;
    if (!collide(nx, hero.y)) hero.x = nx;
    if (!collide(hero.x, ny)) hero.y = ny;
    if (!ONE_SHOT.has(hero.anim)) play(run ? "run" : "walk");
  } else if (!ONE_SHOT.has(hero.anim)) play("idle");

  // advance animation
  const fr = frames(c, hero.anim, hero.facing);
  hero.t += dt;
  while (hero.t >= fr[hero.frame].ms) {
    hero.t -= fr[hero.frame].ms;
    hero.frame++;
    if (hero.frame >= fr.length) {
      if (ONE_SHOT.has(hero.anim)) { play("idle"); break; }
      hero.frame = 0;
    }
  }
  galleryT += dt;
  pressed.clear();
}

function drawSprite(c, f, x, y, g = ctx) {
  const { frame_w: w, frame_h: h } = c.meta;
  g.drawImage(c.img, f.x, f.y, w, h, Math.round(x - w / 2), Math.round(y - h + 1), w, h);
}

function frameAt(fr, t) {
  const total = fr.reduce((s, f) => s + f.ms, 0);
  let k = t % total;
  for (const f of fr) { if (k < f.ms) return f; k -= f.ms; }
  return fr[0];
}

function drawGallery(c) {
  ctx.fillStyle = "#0e0d14"; ctx.fillRect(0, 0, VIEW_W, VIEW_H);
  const anims = Object.keys(c.meta.anims).filter(a => a !== "rotate");
  const facings = c.meta.facings;
  const cw = 44, rh = 36, ox = 60, oy = 14;
  ctx.fillStyle = "#8a8ea6"; ctx.font = "8px monospace";
  facings.forEach((f, i) => ctx.fillText(f.replace("_side", "S").replace("_l", "←"), ox + i * cw + 6, 10));
  anims.forEach((a, r) => {
    ctx.fillStyle = "#8a8ea6"; ctx.fillText(a, 4, oy + r * rh + 22);
    facings.forEach((f, i) => drawSprite(c, frameAt(c.meta.anims[a][f], galleryT), ox + i * cw + 16, oy + r * rh + 32));
  });
}

// Offscreen layers (view-sized): floor, objects, lit objects, emissive, light map.
function layer() {
  const c = document.createElement("canvas");
  c.width = VIEW_W; c.height = VIEW_H;
  const g = c.getContext("2d");
  g.imageSmoothingEnabled = false;
  return [c, g];
}
const [floorC, fctx] = layer(), [objC, octx] = layer(), [litC, lctx] = layer();
const [emC, ectx] = layer(), [lmC, lmctx] = layer();

function draw(fixedT) {
  const c = chars[ci];
  if (gallery) return drawGallery(c);
  const camX = Math.round(Math.max(0, Math.min(MAP_W - VIEW_W, hero.x - VIEW_W / 2)));
  const camY = Math.round(Math.max(0, Math.min(MAP_H - VIEW_H, hero.y - VIEW_H / 2)));
  const now = fixedT ?? performance.now();
  const lit = lightingOn && lighting;
  let dyn = null;

  // floor: tiles + decals, lit with shadows
  fctx.globalCompositeOperation = "source-over";
  fctx.fillStyle = "#07060b"; fctx.fillRect(0, 0, VIEW_W, VIEW_H);
  fctx.drawImage(mapCanvas, -camX, -camY);
  for (const d of animDecals) drawProp(d, camX, camY, now, fctx);
  const fr = frames(c, hero.anim, hero.facing);
  const hf = fr[Math.min(hero.frame, fr.length - 1)];
  const { frame_w: fw, frame_h: fh } = c.meta;
  if (lit) {
    const heroOcc = {
      x0: Math.round(hero.x - fw / 2), y0: Math.round(hero.y - fh + 1), w: fw, h: fh,
      m: alphaMask(c.img, hf.x, hf.y, fw, fh), groundY: Math.round(hero.y) - 1,
    };
    const fl = flyerLights();
    dyn = fl.length ? lighting.dynamicLights(fl, [...lighting.occluders, ...lighting.walls, heroOcc], camX, camY, VIEW_W, VIEW_H) : null;
    lighting.lightMap(lmctx, camX, camY, VIEW_W, VIEW_H, "lit", now, g => {
      g.drawImage(lighting.ao, -camX, -camY);
      lighting.dynamicShadow(g, heroOcc, camX, camY, now);
      for (const fl of flyers) flyerShadow(fl, g, camX, camY, now);
    }, dyn);
    fctx.globalCompositeOperation = "multiply";
    fctx.drawImage(lmC, 0, 0);
    fctx.globalCompositeOperation = "source-over";
    fctx.drawImage(emissiveMap, -camX, -camY);
    for (const d of animDecals) drawProp(d, camX, camY, now, fctx, emissiveImg);
  } else {
    fctx.fillStyle = "#00000066";
    fctx.beginPath(); fctx.ellipse(Math.round(hero.x - camX), Math.round(hero.y - camY), 6, 2, 0, 0, 7); fctx.fill();
  }

  // objects, y-sorted; emissive layer tracks occlusion (erase behind, then add own glow pixels)
  octx.clearRect(0, 0, VIEW_W, VIEW_H);
  ectx.clearRect(0, 0, VIEW_W, VIEW_H);
  const drawHero = () => {
    drawSprite(c, hf, hero.x - camX, hero.y - camY, octx);
    ectx.globalCompositeOperation = "destination-out";
    drawSprite(c, hf, hero.x - camX, hero.y - camY, ectx);
    ectx.globalCompositeOperation = "source-over";
  };
  let heroDrawn = false;
  for (const p of props.slice().sort((a, b) => a.y - b.y)) {
    if (!heroDrawn && p.y > hero.y) { drawHero(); heroDrawn = true; }
    drawProp(p, camX, camY, now, octx);
    ectx.globalCompositeOperation = "destination-out";
    drawProp(p, camX, camY, now, ectx);
    ectx.globalCompositeOperation = "source-over";
    drawProp(p, camX, camY, now, ectx, emissiveImg);
  }
  if (!heroDrawn) drawHero();

  ctx.drawImage(floorC, 0, 0);
  if (lit) {
    // objects lit without shadows (no self-shadowing), alpha restored from the object layer
    lighting.lightMap(lmctx, camX, camY, VIEW_W, VIEW_H, "raw", now, null, dyn);
    lctx.globalCompositeOperation = "source-over";
    lctx.clearRect(0, 0, VIEW_W, VIEW_H);
    lctx.drawImage(objC, 0, 0);
    lctx.globalCompositeOperation = "multiply";
    lctx.drawImage(lmC, 0, 0);
    lctx.globalCompositeOperation = "destination-in";
    lctx.drawImage(objC, 0, 0);
    ctx.drawImage(litC, 0, 0);
    ctx.drawImage(emC, 0, 0);
    // strong moving lights overexpose: add part of their (shadowed) light on top
    if (dyn) {
      ctx.globalCompositeOperation = "lighter";
      ctx.globalAlpha = FLYOVER.bloom;
      lighting.drawDynamic(ctx, dyn, "lit");
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
    }
  } else {
    ctx.drawImage(objC, 0, 0);
  }
  if (lit) drawGlows(camX, camY, now);  // lighting off: plain pixel art, no colored halos
  for (const fl of flyers.slice().sort((a, b) => a.y - b.y)) drawFlyer(fl, camX, camY, now, lit);
  if (hud) {
    ctx.fillStyle = "#cfd3e6"; ctx.font = "8px monospace";
    ctx.fillText(`${c.meta.name}  ${hero.anim}/${hero.facing}  f${hero.frame}  light:${lightingOn ? "on" : "off"} [L]  dark:${Math.round(darkness * 100)}% [-/+]`, 4, 10);
  }
}

// Scene darkness (keys - and +, 0-100%, default LIGHTING.darkness): dims the ambient light, the moon and the light
// on flying cars; neon, fire, lamps and headlights keep their strength, so at 100% the roof
// is dark except for pools of light. The moon is baked, so a change recolors its cached attenuation.
const LIGHT_BASE = { ambient: LIGHTING.ambient, moon: LIGHTING.moon.color, car: LIGHTING.carLight };
const DARKEST = 0.12;  // share of ambient/moon light left at 100% darkness
let darkness = 0, rebake = 0;
const dimHex = (hex, k) => "#" + [1, 3, 5].map(i => Math.round(parseInt(hex.slice(i, i + 2), 16) * k)
  .toString(16).padStart(2, "0")).join("");
function setDarkness(v, rebakeLights = true) {
  darkness = Math.round(Math.max(0, Math.min(1, v)) * 10) / 10;
  const k = 1 - (1 - DARKEST) * darkness;
  LIGHTING.ambient = dimHex(LIGHT_BASE.ambient, k);
  LIGHTING.moon.color = dimHex(LIGHT_BASE.moon, k);
  LIGHTING.carLight = dimHex(LIGHT_BASE.car, Math.max(0.3, k));
  carSprites.clear();
  if (!rebakeLights) return;
  clearTimeout(rebake);
  rebake = setTimeout(() => {
    const t0 = performance.now();
    lighting.recolorMoon();
    console.log(`lighting: ${lighting.lights.length} lights, ${lighting.occluders.length} occluders, recolored in ${(performance.now() - t0).toFixed(1)} ms`);
  }, 60);
}
setDarkness(LIGHTING.darkness ?? 0, false);  // startup default; the first bake uses it

let last = performance.now(), paused = false;
function loop(now) {
  const dt = Math.min(50, now - last); last = now;
  if (!paused) { update(dt); draw(); }
  requestAnimationFrame(loop);
}

(async () => {
  const names = await (await fetch(BASE + "index.json", { cache: "no-store" })).json();
  chars = await Promise.all(names.map(loadCharacter));
  await loadDitherNoise();
  await loadLevel();
  ci = Math.min(1, chars.length - 1);  // the first real character (index 0 is the bare template)
  window.__game = { hero, chars, keys, props, solids, lighting: () => lighting, setLighting: v => { lightingOn = v; },
    flyer: () => flyers[flyers.length - 1] ?? null, flyers: () => flyers,
    autoFly: v => { autoFly = v; }, clearFlyers: () => { flyers = []; },
    // benchmark hooks: render one frame synchronously at a fixed time; place cars
    draw: t => draw(t), setFlyers: list => { flyers = list; }, pause: v => { paused = v; },
    // deterministic capture (README media): advance the simulation by a fixed step, press a key once
    update: dt => update(dt), press: k => pressed.add(k), loopMs: ms => { loopMs = ms; },
    hud: v => { hud = v; }, darkness: v => (v === undefined ? darkness : setDarkness(v)), setCharacter: name => { ci = Math.max(0, chars.findIndex(c => c.name === name)); } };  // debugging / automated checks
  requestAnimationFrame(loop);
})();
