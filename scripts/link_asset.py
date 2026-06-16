"""
Append or link assets from the assets/ library into the active scene.

Usage (inside Blender):
  blender main.blend --python scripts/link_asset.py -- --file assets/props/book.blend --object Book --link
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.project_paths import assets_dir

try:
    import bpy
except ImportError as exc:
    raise SystemExit("Run this script inside Blender.") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Link or append an asset into the scene.")
    parser.add_argument("--file", required=True, help="Path to a .blend asset file")
    parser.add_argument("--object", required=True, help="Object or collection name inside the asset file")
    parser.add_argument("--link", action="store_true", help="Link instead of append")
    parser.add_argument(
        "--collection",
        action="store_true",
        help="Treat --object as a collection name instead of an object name",
    )
    return parser.parse_args(argv)


def _resolve_asset_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        fallback = assets_dir() / Path(raw_path).name
        if fallback.exists():
            return fallback
    return path


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv or [])
    asset_path = _resolve_asset_path(args.file)
    if not asset_path.exists():
        raise SystemExit(f"Asset file not found: {asset_path}")

    directory = "Collection" if args.collection else "Object"
    filepath = str(asset_path)
    filename = args.object

    if args.link:
        bpy.ops.wm.link(directory=f"{directory}/{filename}", filename=filename, filepath=filepath)
    else:
        bpy.ops.wm.append(directory=f"{directory}/{filename}", filename=filename, filepath=filepath)

    print(f"{'Linked' if args.link else 'Appended'} {args.object} from {asset_path}")


if __name__ == "__main__":
    script_args = []
    if "--" in sys.argv:
        script_args = sys.argv[sys.argv.index("--") + 1 :]
    main(script_args)