"""
Initialize the main Blender file for the book-animations project.

Run inside Blender:
  blender --python scripts/init_project.py

Or from Blender's Scripting workspace:
  exec(open("scripts/init_project.py").read())
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.project_paths import ensure_directories, load_config, main_blend_path, project_root

try:
    import bpy
except ImportError as exc:
    raise SystemExit(
        "This script must be run inside Blender (bpy is unavailable)."
    ) from exc


def _clear_default_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def _setup_render_settings(config: dict) -> None:
    scene = bpy.context.scene
    defaults = config["render_defaults"]
    scene.render.resolution_x = defaults["resolution_x"]
    scene.render.resolution_y = defaults["resolution_y"]
    scene.render.fps = defaults["fps"]
    scene.render.engine = defaults["engine"]

    if defaults["engine"] == "CYCLES" and hasattr(scene, "cycles"):
        scene.cycles.samples = defaults["samples"]

    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(project_root() / config["paths"]["renders"] / "frame_")


def _create_starter_objects() -> None:
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"

    bpy.ops.object.light_add(type="SUN", location=(5, -5, 10))
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 3.0

    bpy.ops.object.camera_add(location=(7, -7, 5))
    camera = bpy.context.active_object
    camera.name = "MainCamera"
    camera.rotation_euler = (1.1, 0.0, 0.8)
    bpy.context.scene.camera = camera

    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
    placeholder = bpy.context.active_object
    placeholder.name = "ScenePlaceholder"


def _create_collections(config: dict) -> None:
    scene = bpy.context.scene
    root = scene.collection

    for name in ("Characters", "Environments", "Props", "Cameras", "Lights"):
        if name not in bpy.data.collections:
            col = bpy.data.collections.new(name)
            root.children.link(col)

    scene["book_project"] = config["name"]
    scene["book_project_version"] = config["version"]


def main() -> None:
    ensure_directories()
    config = load_config()
    _clear_default_scene()
    _setup_render_settings(config)
    _create_starter_objects()
    _create_collections(config)

    blend_path = main_blend_path()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"Created main project file: {blend_path}")


if __name__ == "__main__":
    main()