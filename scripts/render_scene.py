"""
Batch render utility for book-animations scenes.

Usage (inside Blender):
  blender main.blend --background --python scripts/render_scene.py -- --output renders/preview
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.project_paths import load_config, renders_dir

try:
    import bpy
except ImportError as exc:
    raise SystemExit("Run this script inside Blender.") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the active Blender scene.")
    parser.add_argument("--output", default="", help="Output directory or filepath prefix")
    parser.add_argument("--frame-start", type=int, default=None)
    parser.add_argument("--frame-end", type=int, default=None)
    parser.add_argument("--animation", action="store_true", help="Render animation instead of a single frame")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv or [])
    config = load_config()
    scene = bpy.context.scene

    if args.frame_start is not None:
        scene.frame_start = args.frame_start
    if args.frame_end is not None:
        scene.frame_end = args.frame_end

    output = args.output.strip()
    if not output:
        output = str(renders_dir() / scene.name)

    output_path = Path(output)
    if output_path.suffix:
        scene.render.filepath = str(output_path.with_suffix(""))
    else:
        output_path.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(output_path / "frame_")

    print(f"Rendering to: {scene.render.filepath}")
    if args.animation:
        bpy.ops.render.render(animation=True, write_still=True)
    else:
        bpy.ops.render.render(write_still=True)

    print("Render complete.")


if __name__ == "__main__":
    script_args = []
    if "--" in sys.argv:
        script_args = sys.argv[sys.argv.index("--") + 1 :]
    main(script_args)