"""
Scene 01 - The Feast Hall
Creates szeth_feast_hall_scene_01.blend with environment, characters, lighting,
camera animation, and crowd/Szeth keyframe animation.

Run:
  blender --background --python scripts/create_scene_01_feast_hall.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENE_PATH = PROJECT_ROOT / "scenes" / "szeth_feast_hall_scene_01.blend"
PREVIEW_PATH = PROJECT_ROOT / "renders" / "szeth_feast_hall_scene_01_preview.png"

FPS = 24
FRAME_START = 1
FRAME_END = 240
EYE_TURN_FRAME = 144  # 6 seconds

try:
    import bpy
    from mathutils import Euler, Vector
except ImportError as exc:
    raise SystemExit("Run inside Blender.") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)
    for block in bpy.data.lights:
        bpy.data.lights.remove(block)
    for block in bpy.data.cameras:
        bpy.data.cameras.remove(block)


def make_material(
    name: str,
    base_color: tuple[float, float, float],
    roughness: float = 0.55,
    metallic: float = 0.0,
    emission: tuple[float, float, float] | None = None,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def assign_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    if obj.data and hasattr(obj.data, "materials"):
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)


def new_mesh_object(name: str, mesh: bpy.types.Mesh) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def link_to_collection(obj: bpy.types.Object, collection_name: str) -> None:
    col = bpy.data.collections.get(collection_name)
    if col is None:
        col = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(col)
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col.objects.link(obj)


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def build_materials() -> dict[str, bpy.types.Material]:
    return {
        "stone": make_material("Stone", (0.42, 0.38, 0.34), roughness=0.85),
        "stone_dark": make_material("StoneDark", (0.28, 0.25, 0.22), roughness=0.9),
        "gold": make_material("Gold", (0.83, 0.65, 0.18), roughness=0.25, metallic=1.0),
        "red_cloth": make_material("RedCloth", (0.45, 0.05, 0.06), roughness=0.75),
        "white_fabric": make_material("WhiteFabric", (0.92, 0.91, 0.88), roughness=0.7),
        "skin_pale": make_material("SkinPale", (0.86, 0.78, 0.72), roughness=0.45),
        "hair_dark": make_material("HairDark", (0.08, 0.06, 0.05), roughness=0.6),
        "noble_red": make_material("NobleRed", (0.55, 0.08, 0.1), roughness=0.65),
        "noble_gold": make_material("NobleGold", (0.75, 0.55, 0.15), roughness=0.35, metallic=0.8),
        "candle_flame": make_material(
            "CandleFlame", (1.0, 0.55, 0.15), emission=(1.0, 0.6, 0.2), emission_strength=8.0
        ),
        "eye_white": make_material("EyeWhite", (0.95, 0.95, 0.95), roughness=0.2),
        "eye_dark": make_material("EyeDark", (0.12, 0.1, 0.09), roughness=0.15),
    }


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def build_hall(mats: dict[str, bpy.types.Material]) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []

    # Floor
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "HallFloor"
    assign_material(floor, mats["stone_dark"])
    objects.append(floor)

    # Vaulted ceiling panels
    for i, x in enumerate(range(-24, 25, 12)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 11))
        panel = bpy.context.active_object
        panel.name = f"CeilingPanel_{i}"
        panel.scale = (5.5, 18, 0.4)
        assign_material(panel, mats["stone"])
        objects.append(panel)

    # Side walls (recessed Asian stone screens)
    for side, x in (("Left", -22), ("Right", 22)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 5))
        wall = bpy.context.active_object
        wall.name = f"Wall_{side}"
        wall.scale = (0.6, 20, 10)
        assign_material(wall, mats["stone"])
        objects.append(wall)

    # Dragon pillars
    pillar_positions = [(-16, y, 0) for y in range(-14, 15, 7)] + [(16, y, 0) for y in range(-14, 15, 7)]
    for idx, (x, y, _z) in enumerate(pillar_positions):
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1.1, depth=12, location=(x, y, 6))
        pillar = bpy.context.active_object
        pillar.name = f"DragonPillar_{idx:02d}"
        assign_material(pillar, mats["stone"])

        # Dragon relief ring
        bpy.ops.mesh.primitive_torus_add(
            major_radius=1.25, minor_radius=0.18, location=(x, y, 7.5), rotation=(math.pi / 2, 0, 0)
        )
        dragon_ring = bpy.context.active_object
        dragon_ring.name = f"DragonCarving_{idx:02d}"
        assign_material(dragon_ring, mats["gold"])
        objects.extend([pillar, dragon_ring])

    # Raised musician platform (far end)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -17, 0.6))
    platform = bpy.context.active_object
    platform.name = "MusicianPlatform"
    platform.scale = (14, 3, 1.2)
    assign_material(platform, mats["stone"])
    objects.append(platform)

    for i, x in enumerate([-4, 0, 4]):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.35, depth=1.6, location=(x, -17, 1.8))
        musician = bpy.context.active_object
        musician.name = f"Musician_{i}"
        assign_material(musician, mats["noble_gold"])
        objects.append(musician)

    return objects


def build_tables_and_chandeliers(mats: dict[str, bpy.types.Material]) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []
    table_centers = [
        (x, y, 0)
        for y in range(-10, 11, 5)
        for x in range(-10, 11, 5)
        if abs(x) > 2 or abs(y) > 2
    ]

    for idx, (x, y, _z) in enumerate(table_centers):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1.8, depth=0.12, location=(x, y, 0.85))
        table = bpy.context.active_object
        table.name = f"BanquetTable_{idx:02d}"
        assign_material(table, mats["red_cloth"])
        objects.append(table)

        # Chandelier above every other table
        if idx % 2 == 0:
            cx, cy, cz = x, y, 9.5
            bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=2.5, location=(cx, cy, cz))
            chain = bpy.context.active_object
            chain.name = f"ChandelierChain_{idx:02d}"
            assign_material(chain, mats["gold"])

            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55, location=(cx, cy, cz - 1.6))
            fixture = bpy.context.active_object
            fixture.name = f"Chandelier_{idx:02d}"
            assign_material(fixture, mats["gold"])
            objects.extend([chain, fixture])

            # Warm point light per chandelier
            light_data = bpy.data.lights.new(name=f"CandleLight_{idx:02d}", type="POINT")
            light_data.color = (1.0, 0.72, 0.38)
            light_data.energy = 350
            light_data.shadow_soft_size = 0.8
            light_obj = bpy.data.objects.new(f"CandleLight_{idx:02d}", light_data)
            light_obj.location = (cx, cy, cz - 1.8)
            bpy.context.collection.objects.link(light_obj)
            objects.append(light_obj)

    # Extra overhead candelabra row
    for i, x in enumerate(range(-18, 19, 6)):
        light_data = bpy.data.lights.new(name=f"OverheadAmber_{i}", type="AREA")
        light_data.color = (1.0, 0.68, 0.32)
        light_data.energy = 180
        light_data.size = 1.2
        light_obj = bpy.data.objects.new(f"OverheadAmber_{i}", light_data)
        light_obj.location = (x, 0, 10)
        light_obj.rotation_euler = (math.pi, 0, 0)
        bpy.context.collection.objects.link(light_obj)
        objects.append(light_obj)

    return objects


# ---------------------------------------------------------------------------
# Characters
# ---------------------------------------------------------------------------

def build_simple_noble(
    name: str,
    location: tuple[float, float, float],
    mats: dict[str, bpy.types.Material],
    rotation_z: float = 0.0,
) -> bpy.types.Object:
    x, y, z = location
    parts: list[bpy.types.Object] = []

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=(x, y, z + 1.55))
    head = bpy.context.active_object
    head.name = f"{name}_Head"
    assign_material(head, mats["skin_pale"])
    parts.append(head)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.28, depth=0.9, location=(x, y, z + 1.0))
    torso = bpy.context.active_object
    torso.name = f"{name}_Torso"
    assign_material(torso, mats["noble_red"])
    parts.append(torso)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.32, depth=0.5, location=(x, y, z + 0.45))
    skirt = bpy.context.active_object
    skirt.name = f"{name}_Lower"
    assign_material(skirt, mats["noble_gold"])
    parts.append(skirt)

    empty = bpy.data.objects.new(name, None)
    empty.location = (x, y, z)
    empty.rotation_euler = (0, 0, rotation_z)
    bpy.context.collection.objects.link(empty)
    for p in parts:
        p.parent = empty

    return empty


def build_crowd(mats: dict[str, bpy.types.Material]) -> bpy.types.Object:
    crowd_root = bpy.data.objects.new("Crowd", None)
    bpy.context.collection.objects.link(crowd_root)

    seed = 0
    for ty, y in enumerate(range(-12, 13, 2)):
        for tx, x in enumerate(range(-12, 13, 2)):
            if abs(x) < 3 and abs(y) < 3:
                continue
            # Leave space near Szeth's pillar (left wall)
            if x < -13 and -8 < y < 2:
                continue
            seed += 1
            angle = (seed * 37) % 360
            noble = build_simple_noble(
                f"Noble_{seed:03d}",
                (x + ((seed % 5) * 0.1), y + ((seed % 3) * 0.1), 0),
                mats,
                rotation_z=math.radians(angle),
            )
            noble.parent = crowd_root

            # Celebratory motion keyframes (body bob + slight turn)
            base = noble.location.copy()
            for frame, dz, rz in (
                (1, 0.0, angle),
                (30, 0.04, angle + 4),
                (60, 0.0, angle - 3),
                (90, 0.05, angle + 6),
                (120, 0.0, angle - 2),
                (150, 0.04, angle + 5),
                (180, 0.0, angle),
                (210, 0.05, angle + 3),
                (240, 0.0, angle),
            ):
                noble.location = (base.x, base.y, base.z + dz)
                noble.rotation_euler = (0, 0, math.radians(rz))
                noble.keyframe_insert(data_path="location", frame=frame)
                noble.keyframe_insert(data_path="rotation_euler", frame=frame)

    return crowd_root


def build_szeth(mats: dict[str, bpy.types.Material]) -> bpy.types.Object:
    """Szeth: pale young man, white tunic, standing still at left pillar."""
    szeth_x, szeth_y = -17.2, -3.5
    root = bpy.data.objects.new("SZETH", None)
    root.location = (szeth_x, szeth_y, 0)
    root.rotation_euler = (0, 0, math.radians(92))
    bpy.context.collection.objects.link(root)

    # Legs
    for side, ox in (("L", -0.12), ("R", 0.12)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.09, depth=0.9, location=(szeth_x + ox, szeth_y, 0.45))
        leg = bpy.context.active_object
        leg.name = f"Szeth_Leg_{side}"
        assign_material(leg, mats["white_fabric"])
        leg.parent = root

    # Torso / white tunic
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.75, location=(szeth_x, szeth_y + 0.05, 1.05))
    torso = bpy.context.active_object
    torso.name = "Szeth_Torso"
    assign_material(torso, mats["white_fabric"])
    torso.parent = root

    # Wrapped waist cloth
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.24, minor_radius=0.07, location=(szeth_x, szeth_y, 0.82), rotation=(math.pi / 2, 0, 0)
    )
    waist = bpy.context.active_object
    waist.name = "Szeth_WaistWrap"
    assign_material(waist, mats["white_fabric"])
    waist.parent = root

    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.19, location=(szeth_x, szeth_y + 0.08, 1.52))
    head = bpy.context.active_object
    head.name = "Szeth_Head"
    assign_material(head, mats["skin_pale"])
    head.parent = root

    # Short dark hair cap
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.2, location=(szeth_x, szeth_y + 0.05, 1.6), scale=(1, 1, 0.55)
    )
    hair = bpy.context.active_object
    hair.name = "Szeth_Hair"
    assign_material(hair, mats["hair_dark"])
    hair.parent = root

    # Eyes (separate for animation)
    eyes_empty = bpy.data.objects.new("Szeth_Eyes", None)
    eyes_empty.parent = head
    eyes_empty.location = head.location
    bpy.context.collection.objects.link(eyes_empty)

    for side, ox in (("L", -0.06), ("R", 0.06)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.035, location=(szeth_x + ox, szeth_y + 0.22, 1.54))
        eye_white = bpy.context.active_object
        eye_white.name = f"Szeth_EyeWhite_{side}"
        assign_material(eye_white, mats["eye_white"])
        eye_white.parent = eyes_empty

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.018, location=(szeth_x + ox, szeth_y + 0.26, 1.54))
        pupil = bpy.context.active_object
        pupil.name = f"Szeth_Pupil_{side}"
        assign_material(pupil, mats["eye_dark"])
        pupil.parent = eye_white

    # Szeth remains motionless — lock root transform keyframes at origin
    for frame in (1, FRAME_END):
        root.keyframe_insert(data_path="location", frame=frame)
        root.keyframe_insert(data_path="rotation_euler", frame=frame)

    # Eyes turn to camera at 6 seconds
    eyes_empty.rotation_euler = (0, 0, 0)
    eyes_empty.keyframe_insert(data_path="rotation_euler", frame=1)
    eyes_empty.keyframe_insert(data_path="rotation_euler", frame=EYE_TURN_FRAME - 1)
    eyes_empty.rotation_euler = (0, math.radians(-35), 0)
    eyes_empty.keyframe_insert(data_path="rotation_euler", frame=EYE_TURN_FRAME)
    eyes_empty.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)

    link_to_collection(root, "Characters")
    return root


# ---------------------------------------------------------------------------
# Lighting & Camera
# ---------------------------------------------------------------------------

def setup_lighting(mats: dict[str, bpy.types.Material], szeth: bpy.types.Object) -> None:
    # Warm hall ambience
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.02, 0.015, 0.01, 1.0)
        bg.inputs["Strength"].default_value = 0.15

    # Cool shadow fill near Szeth's pillar
    cool = bpy.data.lights.new("SzethCoolFill", type="AREA")
    cool.color = (0.55, 0.65, 0.85)
    cool.energy = 60
    cool.size = 3.0
    cool_obj = bpy.data.objects.new("SzethCoolFill", cool)
    cool_obj.location = (-19, -3, 4)
    cool_obj.rotation_euler = (math.radians(70), 0, math.radians(-30))
    bpy.context.collection.objects.link(cool_obj)

    # Subtle rim on Szeth
    rim = bpy.data.lights.new("SzethRim", type="SPOT")
    rim.color = (0.9, 0.75, 0.55)
    rim.energy = 280
    rim.spot_size = math.radians(40)
    rim_obj = bpy.data.objects.new("SzethRim", rim)
    rim_obj.location = (-14, -1, 3)
    rim_obj.rotation_euler = (math.radians(65), 0, math.radians(200))
    bpy.context.collection.objects.link(rim_obj)


def setup_camera(szeth: bpy.types.Object) -> bpy.types.Object:
    cam_data = bpy.data.cameras.new("FeastHallCamera")
    cam_data.lens = 35
    cam_data.clip_end = 500
    cam = bpy.data.objects.new("FeastHallCamera", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    szeth_focus = Vector(szeth.location) + Vector((0, 0.2, 1.5))
    face_focus = szeth_focus + Vector((0, 0.15, 0.05))

    keyframes = [
        (1, Vector((2, 22, 14)), szeth_focus + Vector((0, 8, 0))),
        (72, Vector((-4, 10, 6)), szeth_focus + Vector((2, 4, 0))),
        (120, Vector((-13, -5, 2.8)), szeth_focus),
        (180, Vector((-15.2, -4.8, 1.72)), face_focus),
        (FRAME_END, Vector((-15.4, -4.6, 1.68)), face_focus),
    ]

    for frame, loc, target in keyframes:
        cam.location = loc
        direction = target - loc
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cam.keyframe_insert(data_path="location", frame=frame)
        cam.keyframe_insert(data_path="rotation_euler", frame=frame)

    return cam


def setup_render(preview: bool = True) -> None:
    scene = bpy.context.scene
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.fps = FPS
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48 if preview else 128
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1280 if preview else 1920
    scene.render.resolution_y = 720 if preview else 1080
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.exposure = 0.6


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_scene() -> None:
    reset_scene()
    mats = build_materials()

    for obj in build_hall(mats):
        link_to_collection(obj, "Environments")
    for obj in build_tables_and_chandeliers(mats):
        link_to_collection(obj, "Environments")

    crowd = build_crowd(mats)
    link_to_collection(crowd, "Characters")

    szeth = build_szeth(mats)
    setup_lighting(mats, szeth)
    setup_camera(szeth)
    setup_render(preview=True)

    bpy.context.scene.name = "Scene01_FeastHall"
    SCENE_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(SCENE_PATH))
    print(f"Saved scene: {SCENE_PATH}")


def render_preview() -> None:
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.frame_set(EYE_TURN_FRAME)
    bpy.context.scene.render.filepath = str(PREVIEW_PATH.with_suffix(""))
    bpy.ops.render.render(write_still=True)
    print(f"Rendered preview: {PREVIEW_PATH}")


def main() -> None:
    build_scene()
    render_preview()


if __name__ == "__main__":
    main()