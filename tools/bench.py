"""Render benchmark + image-quality guard for the playground.

Places 0/1/3/5 flying cars at fixed positions in view, renders frames synchronously
(`__game.draw(t)`) and reports mean / p95 ms per frame. With --save it stores reference
frames (fixed time) in build/bench/ref_*.png; with --compare it diffs the current frames
against them and reports max / mean per-channel difference and the share of changed pixels.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build/bench"
OUT.mkdir(parents=True, exist_ok=True)
mode = sys.argv[1] if len(sys.argv) > 1 else ""

CARS = {
    0: [],
    1: [(220, 150, 1, "flycar_red")],
    3: [(120, 120, 1, "flycar_taxi"), (250, 170, -1, "flycar_police"), (340, 90, 1, "flycar")],
    5: [(80, 110, 1, "flycar_taxi"), (180, 190, -1, "flycar_police"), (260, 140, 1, "flycar"),
        (330, 80, -1, "flycar_black"), (390, 200, 1, "flycar_red")],
}

srv = subprocess.Popen([sys.executable, "-m", "http.server", "8771"], cwd=ROOT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
results = {}
try:
    time.sleep(0.7)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 860})
        page.goto("http://localhost:8771/web/")
        page.wait_for_function("window.__game && window.__game.chars.length > 0 && window.__game.lighting()")
        page.evaluate("window.__game.autoFly(false); window.__game.clearFlyers();"
                      "const h = window.__game.hero; h.x = 216; h.y = 132;")
        page.wait_for_timeout(300)
        page.evaluate("window.__game.pause(true); Object.assign(window.__game.hero, {anim: 'idle', facing: 'down', frame: 0, t: 0})")
        for n, cars in CARS.items():
            spec = json.dumps([{"x": x, "y": y, "dir": d, "car": c, "endX": d * 1e9, "t0": 0} for x, y, d, c in cars])
            timings = page.evaluate(f"""() => {{
                const g = window.__game; g.setFlyers({spec});
                for (let i = 0; i < 10; i++) g.draw(1000 + i * 16);   // warm-up
                const ts = [];
                for (let i = 0; i < 120; i++) {{ const t0 = performance.now(); g.draw(2000 + i * 16); ts.push(performance.now() - t0); }}
                g.draw(5000);                                          // fixed frame for the quality check
                return ts; }}""")
            ts = sorted(timings)
            results[n] = {"mean_ms": round(sum(ts) / len(ts), 2), "p95_ms": round(ts[int(len(ts) * 0.95)], 2)}
            data = page.evaluate("document.getElementById('game').toDataURL('image/png')")
            import base64, io
            img = np.array(Image.open(io.BytesIO(base64.b64decode(data.split(",")[1]))).convert("RGB")).astype(int)
            ref = OUT / f"ref_{n}.png"
            if mode == "--save":
                Image.fromarray(img.astype(np.uint8)).save(ref)
            elif mode == "--compare" and ref.exists():
                r = np.array(Image.open(ref).convert("RGB")).astype(int)
                d = np.abs(img - r)
                results[n].update({"max_diff": int(d.max()), "mean_diff": round(float(d.mean()), 3),
                                   "changed_px_pct": round(float((d.max(-1) > 8).mean() * 100), 3)})
                Image.fromarray((np.clip(d * 8, 0, 255)).astype(np.uint8)).save(OUT / f"diff_{n}.png")
            Image.fromarray(img.astype(np.uint8)).save(OUT / f"cur_{n}.png")
        b.close()
finally:
    srv.terminate()
for n, r in results.items():
    print(f"cars={n}: {r}")
