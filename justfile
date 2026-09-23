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
