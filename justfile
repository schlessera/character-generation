# Pixel character generation: template -> labels -> recipes -> sprite sheets -> playground.
# `just` lists all recipes.

default:
    @just --list --unsorted

# ---------------------------------------------------------------- setup & build

# Install Python dependencies (and the headless browser used by the tests)
setup:
    uv sync
    uv run playwright install chromium

# Build everything the playground needs into web/data (props atlas + all character sheets)
build *names: props
    uv run python -m chargen build {{names}}

# Serve the playground at http://localhost:8000
serve port="8000":
    uv run python -m http.server {{port}} --directory web

# Build, then serve
play: build serve

# ---------------------------------------------------------------- characters

# Preview a character: every animation x facing (optionally only some anims) + big idle facings
preview name *anims:
    uv run python -m chargen preview {{name}} {{anims}}

# Print a character's head grids aligned with the template's head outlines, for editing
heads name:
    uv run python -m chargen heads {{name}}

# Pixel mockup (snapped to its grid) above the render, per view + head close-ups -> build/preview/NAME_compare.png
# Flags: --text VIEW --fit --optimize --ceiling --slack --split --widths --digits VIEW --shift --fit-grid VIEW --recipe FILE
compare name *flags:
    uv run python -m chargen compare {{name}} {{flags}}

# The eight idle facings cropped to frame rows y0,y1 at 16x, one row per --recipe variant (--diff marks changes) -> build/preview/NAME_crops.png
crops name *flags:
    uv run python -m chargen crops {{name}} {{flags}}

# Static checks on a recipe: parts order, one-sided rules with mirrored facings, legend, grids
lint name:
    uv run python -m chargen lint {{name}}

# One image to look at after a change: facings, torso and feet crops, turn-around, angled animations -> build/preview/NAME_review.png
review name:
    uv run python -m chargen review {{name}}

# Print a head grid with row numbers, or set one of its rows: `just grid NAME VIEW 7 '..kbbbk..'`
grid name view *args:
    uv run python -m chargen grid {{name}} {{view}} {{args}}

# GIF of the character turning through the eight facings (idle; add anims for more) -> build/preview/NAME_turntable.gif
turntable name *flags:
    uv run python -m chargen turntable {{name}} {{flags}}

# Score, append a row to history/NOTES.md, snapshot every fifth step (or --snapshot); --amend replaces the last row
step name message *flags:
    uv run python -m chargen step {{name}} "{{message}}" {{flags}}

# Exercise every compare flag and the lint/review/step/crops commands on a scratch copy of juno
selftest:
    uv run python tools/selftest.py

# ---------------------------------------------------------------- template labels

# Validate the per-frame body-part label files (all, or the given frame numbers)
check-labels *frames:
    uv run python -m chargen.labeltool check {{frames}}

# Contact sheet of template frames colored by body part -> build/preview/labels*.png
labels *anims:
    uv run python -m chargen labels {{anims}}

# Original | labels | overlay for single frames -> build/labels_preview.png
label-frames +frames:
    uv run python -m chargen.labeltool render {{frames}} -o build/labels_preview.png

# 16x zoomed reference frames with a pixel grid -> build/frames_zoom/
label-zoom *frames:
    uv run python -m chargen.labeltool zoom {{frames}}

# ---------------------------------------------------------------- props & tiles

# Validate and pack the hand-drawn props/tiles into web/data/props (+ build/preview/props.png)
props:
    uv run python -m chargen.pixeltool check
    uv run python -m chargen.props

# Render sprites: reference | 12x | game scale next to the character -> build/pixel/
pixel +names:
    uv run python -m chargen.pixeltool render {{names}}

# New prop: palette-snapped rough draft from its reference art, to redraw by hand
pixel-draft +names:
    uv run python -m chargen.pixeltool draft {{names}}

# Seed animation frames (NAME@k.txt copies of frame 0) for props with `anim`
pixel-frames +names:
    uv run python -m chargen.pixeltool frames {{names}}

# Review a prop animation: frame strip with changed pixels marked + GIF -> build/pixel/
pixel-anim +names:
    uv run python -m chargen.pixeltool anim {{names}}

# Random floor patch mixing the given tiles, to check seams -> build/pixel/floor.png
floor +tiles:
    uv run python -m chargen.pixeltool floor {{tiles}}

# ---------------------------------------------------------------- tests & docs

# Headless browser test: drives the playground with the keyboard, screenshots to build/smoke
smoke: build
    uv run python tools/smoke.py

# Render benchmark (0/1/3/5 flying cars): ms per frame; --save / --compare reference frames
bench *mode:
    uv run python tools/bench.py {{mode}}

# Regenerate the README images in docs/images
media: build
    uv run python tools/media.py
