"""Headless smoke test of the playground: loads the page, drives the character with
the keyboard, checks state transitions and saves screenshots to build/smoke/."""
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build/smoke"
OUT.mkdir(parents=True, exist_ok=True)

server = subprocess.Popen([sys.executable, "-m", "http.server", "8765"], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
errors = []
try:
    time.sleep(0.7)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 860})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else print("console:", m.text))
        page.goto("http://localhost:8765/web/")
        page.wait_for_function("window.__game && window.__game.chars.length > 0")
        state = lambda: page.evaluate("({...window.__game.hero, char: window.__game.chars.length})")
        checks = []

        def step(name, keys, hold_ms, expect):
            for k in keys:
                page.keyboard.down(k)
            page.wait_for_timeout(hold_ms)
            s = state()
            page.screenshot(path=str(OUT / f"{name}.png"))
            for k in keys:
                page.keyboard.up(k)
            ok = all(s[k] == v for k, v in expect.items())
            checks.append((name, ok, {k: s[k] for k in expect}))

        step("idle", [], 300, {"anim": "idle"})
        # animated props: the fire barrel region must change over time
        grab = """() => { const c = document.getElementById('game').getContext('2d');
            const p = window.__game.props.find(p => p.name === 'fire_barrel');
            const cx = Math.max(0, Math.min(448 - 400, window.__game.hero.x - 200));
            const cy = Math.max(0, Math.min(256 - 240, window.__game.hero.y - 120));
            return Array.from(c.getImageData(p.x - cx - 7, p.y - cy - 25, 14, 12).data).join(','); }"""
        shots = set()
        for _ in range(6):
            shots.add(page.evaluate(grab))
            page.wait_for_timeout(60)
        checks.append(("fire_animates", len(shots) > 1, {"distinct_frames": len(shots)}))
        x0 = state()["x"]
        step("walk_right", ["d"], 600, {"anim": "walk", "facing": "side"})
        checks.append(("moved_right", state()["x"] > x0, {"x": state()["x"]}))
        step("run_downleft", ["Shift", "s", "a"], 600, {"anim": "run", "facing": "down_side_l"})
        step("walk_up", ["w"], 400, {"anim": "walk", "facing": "up"})
        page.wait_for_timeout(200)
        step("attack", ["j"], 250, {"anim": "attack"})
        page.wait_for_timeout(1200)
        step("jump", [" "], 200, {"anim": "jump"})
        page.wait_for_timeout(800)
        step("interact", ["e"], 150, {"anim": "interact"})
        page.wait_for_timeout(600)
        page.keyboard.press("l")
        page.wait_for_timeout(150)
        page.screenshot(path=str(OUT / "lighting_off.png"))
        page.keyboard.press("l")
        fps = page.evaluate("""() => new Promise(r => { let n = 0; const t0 = performance.now();
            const f = () => { n++; if (performance.now() - t0 < 1000) requestAnimationFrame(f); else r(n); };
            requestAnimationFrame(f); })""")
        # shared CI runners are slow and GPU-less: report fps there, only enforce it locally
        checks.append(("fps_lit", fps >= 30 or bool(os.environ.get("CI")), {"fps": fps}))
        # shadows never go below "no direct light": light buffer >= ambient everywhere,
        # both with total occlusion and in a real frame (hero next to the fire, several shadows)
        floor = page.evaluate("""() => {
            const L = window.__game.lighting(), amb = L.cfg.ambient;
            const a = [1, 3, 5].map(i => parseInt(amb.slice(i, i + 2), 16));
            const c = document.createElement('canvas'); c.width = 400; c.height = 240;
            const g = c.getContext('2d', { willReadFrequently: true });
            const minBelow = () => { const d = g.getImageData(0, 0, 400, 240).data; let m = 255;
                for (let i = 0; i < d.length; i += 4) for (let k = 0; k < 3; k++) m = Math.min(m, d[i + k] - a[k]);
                return m; };
            L.lightMap(g, 0, 0, 400, 240, 'lit', 0, x => { x.fillStyle = '#000'; x.fillRect(0, 0, 400, 240); });
            const total = minBelow();
            const hero = { x0: 274, y0: 60, w: 32, h: 32, m: new Uint8Array(1024).fill(1), groundY: 91 };
            L.lightMap(g, 0, 0, 400, 240, 'lit', 0, x => { x.drawImage(L.ao, 0, 0); L.dynamicShadow(x, hero, 0, 0, 0); });
            return { total_occlusion: total, real_frame: minBelow() }; }""")
        checks.append(("shadow_floor_is_ambient", floor["total_occlusion"] >= -1 and floor["real_frame"] >= -1, floor))
        # flyover: light must enter and leave smoothly (zero at spawn/exit, peak mid-screen)
        page.evaluate("window.__game.autoFly(false); window.__game.clearFlyers()")
        page.keyboard.press("f")
        series = []
        for k in range(90):
            page.wait_for_timeout(50)
            series.append(page.evaluate("""() => { const L = window.__game.lighting(), f = window.__game.flyer();
                if (!f || !L._dl) return [f ? f.x : null, 0];
                let s = 0; for (const v of L._dl.accRaw) s += v; return [f.x, Math.round(s)]; }"""))
            if k in (30, 40, 50):
                page.screenshot(path=str(OUT / f"flyover_{k}.png"))
        energy = [e for _, e in series]
        peak = max(energy)
        first, last = energy[0], next((e for x, e in reversed(series) if x is not None), 0)
        steps = max(abs(a - b) for a, b in zip(energy, energy[1:]))
        checks.append(("flyover_smooth", first == 0 and peak > 0 and steps < peak * 0.6,
                       {"start": first, "peak": peak, "end": last, "max_step": steps, "done": series[-1][0] is None}))
        # concurrent cars: a new spawn never removes the previous one
        page.keyboard.press("f")
        page.wait_for_timeout(400)
        page.keyboard.press("f")
        page.wait_for_timeout(100)
        n = page.evaluate("window.__game.flyers().length")
        page.screenshot(path=str(OUT / "flyover_two.png"))
        checks.append(("flyers_concurrent", n >= 2, {"on_screen_or_approaching": n}))
        page.keyboard.press("v")
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "gallery.png"))
        page.keyboard.press("v")
        page.keyboard.press("c")
        page.wait_for_timeout(200)
        page.screenshot(path=str(OUT / "template_char.png"))
        b.close()
finally:
    server.terminate()

for name, ok, s in checks:
    print(("PASS" if ok else "FAIL"), name, s)
print("page errors:", errors or "none")
sys.exit(0 if all(ok for _, ok, _ in checks) and not errors else 1)
