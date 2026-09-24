"""Run every chargen command and compare flag on a scratch copy of Juno and check that each
one produced its section or file. Catches the class of bug where a patch leaves a block
indented under the wrong `if` (it happened)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "zzselftest"
CHAR = ROOT / "characters" / NAME


def run(*args):
    p = subprocess.run([sys.executable, "-m", "chargen", *args], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    if CHAR.exists():
        shutil.rmtree(CHAR)
    (CHAR / "concept").mkdir(parents=True)
    (CHAR / "history").mkdir()
    shutil.copy(ROOT / "characters/juno/concept/juno-pixel-mockup.png", CHAR / "concept" / f"{NAME}-pixel-mockup.png")
    shutil.copy(ROOT / ".claude/skills/mockup-character/assets/recipe-skeleton.toml", CHAR / "recipe.toml")
    fails = []
    try:
        rc, out = run("compare", NAME, "--quiet", "--text", "down", "--fit", "--fit-part", "T", "--widths", "--digits", "side",
                      "--slack", "--split", "--hex", "down", "20,24,12,20", "--hot", "5", "--init-palette", "--ceiling", "--goal", "4")
        for want in ("== down: mockup | render", "render color", "== fit on parts", "widths", "cost digits", ": slack", "silhouette=",
                     "mockup hex", "costliest", "palette from the mockup", "ceiling ", "goal "):
            if want not in out:
                fails.append(f"compare flag output missing: {want!r}")
        rc, out = run("compare", NAME, "--quiet", "--draft-grid", "all", "--all-slots", "--clean", "--apply", "--mirror-swap")
        if out.count("written to") != 13 or "second pass" not in out:  # 5 in the first pass, 8 in the second
            fails.append(f"draft-grid all wrote {out.count('written to')} grids, expected 5 + 8 over two passes")
        rc, out = run("compare", NAME, "--quiet", "--shift", "--chars", "kbHDi", "--fit-grid", "down", "--chars", "kbHDi", "--optimize")
        for want in ("best grid shift", "fit-grid down", "optimize:"):
            if want not in out:
                fails.append(f"missing: {want!r}")
        rc, out = run("lint", NAME)
        if "error" in out or "warn " in out:
            fails.append("lint reports an error or warning on the drafted skeleton (it must lint clean):\n" + out)
        rc, out = run("review", NAME)
        if not (ROOT / "build/preview" / f"{NAME}_review.png").exists():
            fails.append("review wrote no image")
        rc, out = run("crops", NAME, "--box", "17,31", "--diff", "--recipe", str(CHAR / "recipe.toml"))
        if not (ROOT / "build/preview" / f"{NAME}_crops.png").exists():
            fails.append("crops wrote no image")
        rc, out = run("step", NAME, "drafted", "--goal", "4")
        rc, out2 = run("step", NAME, "drafted again", "--goal", "4", "--amend")
        rows = [l for l in (CHAR / "history/NOTES.md").read_text().splitlines() if l.startswith("| 0")]
        if len(rows) != 1 or "goal: ceiling" not in out2:
            fails.append("step/--amend/--goal did not behave: " + out2)
        rc, out = run("compare", NAME, "--quiet", "--sweep", "3", "--sweep-parts", "feet")
        if "candidates over" not in out:
            fails.append("--sweep printed no table")
        (CHAR / "try.toml").write_text('[[rules]]\ntype = "rows"\npart = "feet"\nfrom = "bottom"\nn = 1\ncolor = "shoes.shade"\n')
        rc, out = run("compare", NAME, "--quiet", "--try", str(CHAR / "try.toml"))
        if "rule 1:" not in out:
            fails.append("--try printed no row")
    finally:
        shutil.rmtree(CHAR, ignore_errors=True)
        for f in (ROOT / "build/preview").glob(f"{NAME}*"):
            f.unlink()
    if fails:
        print("\n".join("FAIL " + f for f in fails))
        sys.exit(1)
    print("selftest ok")


if __name__ == "__main__":
    main()
