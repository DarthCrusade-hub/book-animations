"""
Scene 01 - The Feast Hall (improved)
Creates szeth_feast_hall_scene_01.blend with cinematic environment,
Szeth character, crowd animation, camera dolly, and Eevee preview render.

Run:
  blender --background --python scripts/create_scene_01_feast_hall.py
"""

from __future__ import annotations

import math
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENE_PATH = PROJECT_ROOT / "scenes" / "szeth_feast_hall_scene_01.blend"
PREVIEW_PATH = PROJECT_ROOT / "renders" / "szeth_feast_hall_scene_01_preview.png"

FPS = 24
FRAME_START = 1
FRAME_END = 240
EYE_TURN_FRAME = 144
PREVIEW_FRAME = 1

try:
    import bpy
    from mathutils import Vector
except ImportError as exc:
    raise SystemExit("Run inside Blender.") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)
    for block in list(bpy.data.materials):
        bpy.data.materials.remove(block)
    for block in list(bpy.data.lights):
        bpy.data.lights.remove(block)
    for block in list(bpy.data.cameras):
        bpy.data.cameras.remove(block)


def link_to_collection(obj: bpy.types.Object, collection_name: str) -> None:
    col = bpy.data.collections.get(collection_name)
    if col is None:
        col = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(col)
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col.objects.link(obj)


def assign_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    if obj.data and hasattr(obj.data, "materials"):
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)


def set_smooth(obj: bpy.types.Object, shade: bool = True) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth() if shade else bpy.ops.object.shade_flat()
    obj.select_set(False)


def keyframe_linear(obj: bpy.types.Object, path: str) -> None:
    if not obj.animation_data or not obj.animation_data.action:
        return
    for fc in obj.animation_data.action.fcurves:
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------------------
# Procedural Materials
# ---------------------------------------------------------------------------

def make_stone_material(name: str, base: tuple[float, float, float], roughness: float = 0.82) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 6.0
    noise.inputs["Detail"].default_value = 8.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*[c * 0.75 for c in base], 1.0)
    ramp.color_ramp.elements[1].color = (*[min(c * 1.15, 1.0) for c in base], 1.0)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35

    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = roughness
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_velvet_material(name: str, color: tuple[float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08

    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.92
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = 0.45
        bsdf.inputs["Sheen Roughness"].default_value = 0.35
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_gold_material(name: str) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 12.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15

    bsdf.inputs["Base Color"].default_value = (0.92, 0.72, 0.22, 1.0)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.18
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_flame_material(name: str) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    grad = nodes.new("ShaderNodeTexGradient")
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (1.0, 0.85, 0.35, 1.0)
    ramp.color_ramp.elements[1].color = (1.0, 0.35, 0.05, 1.0)
    emit.inputs["Strength"].default_value = 18.0

    links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], emit.inputs["Color"])
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def make_skin_material(name: str, tone: tuple[float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*tone, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.42
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.18
        bsdf.inputs["Subsurface Radius"].default_value = (0.8, 0.4, 0.25)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_fabric_material(name: str, color: tuple[float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 40.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12

    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.72
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def build_materials() -> dict[str, bpy.types.Material]:
    return {
        "stone": make_stone_material("WarmStone", (0.52, 0.44, 0.36)),
        "stone_dark": make_stone_material("WarmStoneDark", (0.34, 0.28, 0.24), 0.9),
        "gold": make_gold_material("ChandelierGold"),
        "red_cloth": make_velvet_material("DeepRedCloth", (0.38, 0.02, 0.04)),
        "white_fabric": make_fabric_material("WhiteTunic", (0.94, 0.93, 0.9)),
        "skin_pale": make_skin_material("PaleSkin", (0.9, 0.82, 0.76)),
        "skin_noble": make_skin_material("NobleSkin", (0.78, 0.62, 0.5)),
        "hair_dark": make_fabric_material("DarkHair", (0.07, 0.05, 0.04)),
        "noble_red": make_velvet_material("NobleRobeRed", (0.52, 0.06, 0.08)),
        "noble_gold": make_gold_material("NobleTrimGold"),
        "candle_flame": make_flame_material("AmberFlame"),
        "eye_white": make_fabric_material("EyeWhite", (0.96, 0.96, 0.96)),
        "eye_dark": make_fabric_material("EyeIris", (0.18, 0.14, 0.12)),
        "wood": make_fabric_material("InstrumentWood", (0.35, 0.22, 0.12)),
        "food": make_fabric_material("FeastFood", (0.55, 0.35, 0.15)),
    }


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def add_dragon_carving(pillar: bpy.types.Object, idx: int, mats: dict) -> list[bpy.types.Object]:
    parts = []
    x, y, _ = pillar.location
    for ring_i, z in enumerate([4.5, 6.5, 8.5]):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=1.28 + ring_i * 0.02,
            minor_radius=0.14,
            location=(x, y, z),
            rotation=(math.pi / 2, 0, ring_i * 0.4),
        )
        ring = bpy.context.active_object
        ring.name = f"DragonRing_{idx:02d}_{ring_i}"
        assign_material(ring, mats["gold"])
        parts.append(ring)

    # Serpentine body winding pillar
    for seg in range(6):
        angle = seg * 0.9
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.22,
            location=(x + math.cos(angle) * 1.15, y + math.sin(angle) * 1.15, 4 + seg * 1.1),
        )
        scale_seg = bpy.context.active_object
        scale_seg.name = f"DragonBody_{idx:02d}_{seg}"
        scale_seg.scale = (1.6, 0.7, 0.7)
        assign_material(scale_seg, mats["gold"])
        parts.append(scale_seg)

    return parts


def build_hall(mats: dict[str, bpy.types.Material]) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []

    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "HallFloor"
    assign_material(floor, mats["stone_dark"])
    objects.append(floor)

    for i, x in enumerate(range(-24, 25, 12)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 11.5))
        panel = bpy.context.active_object
        panel.name = f"VaultCeiling_{i}"
        panel.scale = (5.8, 18, 0.35)
        assign_material(panel, mats["stone"])
        objects.append(panel)

    for side, x in (("Left", -21), ("Right", 21)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 5.5))
        wall = bpy.context.active_object
        wall.name = f"StoneWall_{side}"
        wall.scale = (0.8, 20, 10)
        assign_material(wall, mats["stone"])
        objects.append(wall)

        for row in range(4):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x * 0.96, -12 + row * 7, 3 + row * 1.5))
            screen = bpy.context.active_object
            screen.name = f"AsianScreen_{side}_{row}"
            screen.scale = (0.15, 2.5, 1.8)
            assign_material(screen, mats["stone_dark"])
            objects.append(screen)

    pillar_positions = [(-15, y, 0) for y in range(-14, 15, 7)] + [(15, y, 0) for y in range(-14, 15, 7)]
    for idx, (x, y, _z) in enumerate(pillar_positions):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1.15, depth=12, location=(x, y, 6))
        pillar = bpy.context.active_object
        pillar.name = f"DragonPillar_{idx:02d}"
        assign_material(pillar, mats["stone"])
        set_smooth(pillar)
        objects.append(pillar)
        objects.extend(add_dragon_carving(pillar, idx, mats))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -17, 0.55))
    platform = bpy.context.active_object
    platform.name = "MusicianPlatform"
    platform.scale = (14, 3.5, 1.1)
    assign_material(platform, mats["stone"])
    objects.append(platform)

    return objects


def build_chandelier(
    cx: float, cy: float, cz: float, idx: int, mats: dict
) -> list[bpy.types.Object]:
    parts: list[bpy.types.Object] = []

    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=2.8, location=(cx, cy, cz))
    chain = bpy.context.active_object
    chain.name = f"ChandelierChain_{idx:02d}"
    assign_material(chain, mats["gold"])
    parts.append(chain)

    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.75, minor_radius=0.06, location=(cx, cy, cz - 1.5), rotation=(math.pi / 2, 0, 0)
    )
    frame = bpy.context.active_object
    frame.name = f"ChandelierFrame_{idx:02d}"
    assign_material(frame, mats["gold"])
    parts.append(frame)

    for arm_i in range(8):
        angle = arm_i * (math.pi * 2 / 8)
        ax = cx + math.cos(angle) * 0.55
        ay = cy + math.sin(angle) * 0.55
        bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=0.35, location=(ax, ay, cz - 1.65))
        arm = bpy.context.active_object
        arm.name = f"ChandelierArm_{idx:02d}_{arm_i}"
        arm.rotation_euler = (math.radians(20), 0, angle)
        assign_material(arm, mats["gold"])
        parts.append(arm)

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(ax, ay, cz - 1.85))
        flame = bpy.context.active_object
        flame.name = f"CandleFlame_{idx:02d}_{arm_i}"
        flame.scale = (0.5, 0.5, 1.2)
        assign_material(flame, mats["candle_flame"])
        parts.append(flame)

    light_data = bpy.data.lights.new(name=f"ChandelierLight_{idx:02d}", type="POINT")
    light_data.color = (1.0, 0.7, 0.32)
    light_data.energy = 420
    light_data.shadow_soft_size = 1.2
    light_obj = bpy.data.objects.new(f"ChandelierLight_{idx:02d}", light_data)
    light_obj.location = (cx, cy, cz - 1.7)
    bpy.context.collection.objects.link(light_obj)
    parts.append(light_obj)
    return parts


def build_tables_and_chandeliers(mats: dict[str, bpy.types.Material]) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []
    table_centers = [
        (x, y)
        for y in range(-10, 11, 5)
        for x in range(-10, 11, 5)
        if abs(x) > 2 or abs(y) > 2
    ]

    for idx, (x, y) in enumerate(table_centers):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.12, depth=0.82, location=(x, y, 0.41))
        leg = bpy.context.active_object
        leg.name = f"TableLeg_{idx:02d}"
        assign_material(leg, mats["wood"])
        objects.append(leg)

        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.85, depth=0.1, location=(x, y, 0.86))
        table = bpy.context.active_object
        table.name = f"BanquetTable_{idx:02d}"
        assign_material(table, mats["red_cloth"])
        set_smooth(table)
        objects.append(table)

        bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.08, location=(x + 0.5, y, 0.95))
        plate = bpy.context.active_object
        plate.name = f"FeastPlate_{idx:02d}"
        assign_material(plate, mats["gold"])
        objects.append(plate)

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(x - 0.4, y + 0.3, 0.98))
        food = bpy.context.active_object
        food.name = f"FeastFood_{idx:02d}"
        food.scale = (1.2, 1.2, 0.6)
        assign_material(food, mats["food"])
        objects.append(food)

        bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.25, location=(x + 1.0, y - 0.5, 0.92))
        candle = bpy.context.active_object
        candle.name = f"TableCandle_{idx:02d}"
        assign_material(candle, mats["gold"])
        objects.append(candle)

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(x + 1.0, y - 0.5, 1.05))
        tc_flame = bpy.context.active_object
        tc_flame.name = f"TableFlame_{idx:02d}"
        tc_flame.scale = (0.6, 0.6, 1.4)
        assign_material(tc_flame, mats["candle_flame"])
        objects.append(tc_flame)

        if idx % 2 == 0:
            objects.extend(build_chandelier(x, y, 9.8, idx, mats))

    return objects


# ---------------------------------------------------------------------------
# Characters
# ---------------------------------------------------------------------------

def parent_parts(root: bpy.types.Object, parts: list[bpy.types.Object]) -> None:
    for p in parts:
        p.parent = root


def build_musicians(mats: dict[str, bpy.types.Material]) -> list[bpy.types.Object]:
    musicians = []
    configs = [
        (-4.5, "Lute"),
        (0.0, "Drum"),
        (4.5, "Flute"),
        (-2.0, "Harp"),
        (2.0, "Zither"),
    ]
    for i, (x, kind) in enumerate(configs):
        root = bpy.data.objects.new(f"Musician_{i}_{kind}", None)
        root.location = (x, -17, 1.2)
        bpy.context.collection.objects.link(root)
        parts = []

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(x, -17, 1.75))
        head = bpy.context.active_object
        assign_material(head, mats["skin_noble"])
        parts.append(head)

        bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=0.55, location=(x, -17, 1.35))
        torso = bpy.context.active_object
        assign_material(torso, mats["noble_red"])
        parts.append(torso)

        bpy.ops.mesh.primitive_cylinder_add(radius=0.35, depth=0.25, location=(x, -17, 0.95))
        base = bpy.context.active_object
        assign_material(base, mats["noble_gold"])
        parts.append(base)

        if kind == "Lute":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.28, location=(x + 0.35, -16.7, 1.3))
            inst = bpy.context.active_object
            inst.scale = (0.6, 0.3, 1.0)
            assign_material(inst, mats["wood"])
            parts.append(inst)
        elif kind == "Drum":
            bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.18, location=(x, -16.6, 1.0))
            inst = bpy.context.active_object
            assign_material(inst, mats["wood"])
            parts.append(inst)
        elif kind == "Harp":
            bpy.ops.mesh.primitive_cube_add(size=0.6, location=(x + 0.3, -16.7, 1.4))
            inst = bpy.context.active_object
            inst.scale = (0.15, 0.4, 1.0)
            assign_material(inst, mats["gold"])
            parts.append(inst)
        else:
            bpy.ops.mesh.primitive_cube_add(size=0.5, location=(x + 0.25, -16.7, 1.25))
            inst = bpy.context.active_object
            inst.scale = (0.2, 0.5, 0.1)
            assign_material(inst, mats["wood"])
            parts.append(inst)

        parent_parts(root, parts)

        for frame, rz, tz in ((1, 0, 0), (40, 8, 0.03), (80, -6, 0), (120, 10, 0.04), (160, -4, 0), (200, 6, 0.02), (240, 0, 0)):
            root.rotation_euler = (0, 0, math.radians(rz))
            root.location = (x, -17, 1.2 + tz)
            root.keyframe_insert("rotation_euler", frame=frame)
            root.keyframe_insert("location", frame=frame)

        musicians.append(root)
    return musicians


def build_noble(name: str, x: float, y: float, mats: dict, seed: int) -> bpy.types.Object:
    root = bpy.data.objects.new(name, None)
    root.location = (x, y, 0)
    angle = (seed * 41) % 360
    root.rotation_euler = (0, 0, math.radians(angle))
    bpy.context.collection.objects.link(root)

    parts = []
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(x, y, 1.52))
    head = bpy.context.active_object
    head.name = f"{name}_Head"
    assign_material(head, mats["skin_noble"])
    set_smooth(head)
    parts.append(head)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.26, depth=0.75, location=(x, y, 1.05))
    torso = bpy.context.active_object
    torso.name = f"{name}_Torso"
    assign_material(torso, mats["noble_red"] if seed % 2 else mats["noble_gold"])
    parts.append(torso)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=0.45, location=(x, y, 0.5))
    lower = bpy.context.active_object
    lower.name = f"{name}_Lower"
    assign_material(lower, mats["noble_gold"] if seed % 2 else mats["noble_red"])
    parts.append(lower)

    for side, ox in (("L", -0.28), ("R", 0.28)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.07, depth=0.55, location=(x + ox, y, 1.0))
        arm = bpy.context.active_object
        arm.name = f"{name}_Arm_{side}"
        arm.rotation_euler = (math.radians(75 if side == "R" else 70), 0, math.radians(20 if side == "R" else -20))
        assign_material(arm, mats["noble_red"])
        parts.append(arm)

        for frame, rot_x in ((1, 75), (45, 55), (90, 80), (135, 50), (180, 85), (210, 60), (240, 75)):
            arm.rotation_euler = (
                math.radians(rot_x if side == "R" else rot_x - 5),
                0,
                math.radians(20 if side == "R" else -20),
            )
            arm.keyframe_insert("rotation_euler", frame=frame)

    parent_parts(root, parts)

    base_loc = root.location.copy()
    base_rot = angle
    for frame, dz, head_turn, body_turn in (
        (1, 0.0, 0, 0),
        (30, 0.04, 12, 5),
        (60, 0.0, -8, -4),
        (90, 0.05, 15, 7),
        (120, 0.0, -6, -3),
        (150, 0.04, 10, 6),
        (180, 0.0, -10, -5),
        (210, 0.05, 8, 4),
        (240, 0.0, 0, 0),
    ):
        root.location = (base_loc.x, base_loc.y, base_loc.z + dz)
        root.rotation_euler = (0, 0, math.radians(base_rot + body_turn))
        root.keyframe_insert("location", frame=frame)
        root.keyframe_insert("rotation_euler", frame=frame)
        head.rotation_euler = (0, 0, math.radians(head_turn))
        head.keyframe_insert("rotation_euler", frame=frame)

    return root


def build_crowd(mats: dict[str, bpy.types.Material]) -> bpy.types.Object:
    crowd_root = bpy.data.objects.new("Crowd", None)
    bpy.context.collection.objects.link(crowd_root)
    seed = 0
    for y in range(-12, 13, 2):
        for x in range(-12, 13, 2):
            if abs(x) < 3 and abs(y) < 3:
                continue
            if x < -13 and -8 < y < 2:
                continue
            seed += 1
            noble = build_noble(
                f"Noble_{seed:03d}",
                x + ((seed % 5) * 0.12),
                y + ((seed % 3) * 0.1),
                mats,
                seed,
            )
            noble.parent = crowd_root
    return crowd_root


def build_szeth(mats: dict[str, bpy.types.Material]) -> bpy.types.Object:
    """Lean athletic pale young man in white, standing still at left pillar."""
    sx, sy = -16.3, -3.8
    root = bpy.data.objects.new("SZETH", None)
    root.location = (sx, sy, 0)
    root.rotation_euler = (0, 0, math.radians(88))
    bpy.context.collection.objects.link(root)

    def loc(off: Vector) -> Vector:
        return root.location + off

    parts = []

    for side, ox in (("L", -0.1), ("R", 0.1)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.085, depth=0.92, location=loc(Vector((ox, 0.05, 0.46))))
        leg = bpy.context.active_object
        leg.name = f"Szeth_Leg_{side}"
        assign_material(leg, mats["white_fabric"])
        parts.append(leg)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.19, depth=0.62, location=loc(Vector((0, 0.08, 1.02))))
    torso = bpy.context.active_object
    torso.name = "Szeth_Torso"
    torso.scale = (0.85, 0.75, 1.0)
    assign_material(torso, mats["white_fabric"])
    parts.append(torso)

    bpy.ops.mesh.primitive_cube_add(size=0.42, location=loc(Vector((0, 0.1, 1.22))))
    chest = bpy.context.active_object
    chest.name = "Szeth_Chest"
    chest.scale = (0.7, 0.45, 0.55)
    assign_material(chest, mats["white_fabric"])
    parts.append(chest)

    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.21,
        minor_radius=0.065,
        location=loc(Vector((0, 0.04, 0.84))),
        rotation=(math.pi / 2, 0, 0),
    )
    waist = bpy.context.active_object
    waist.name = "Szeth_WaistWrap"
    assign_material(waist, mats["white_fabric"])
    parts.append(waist)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.055, depth=0.14, location=loc(Vector((0, 0.1, 1.38))))
    neck = bpy.context.active_object
    neck.name = "Szeth_Neck"
    assign_material(neck, mats["skin_pale"])
    parts.append(neck)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.17, location=loc(Vector((0, 0.12, 1.52))))
    head = bpy.context.active_object
    head.name = "Szeth_Head"
    head.scale = (0.88, 0.92, 1.02)
    assign_material(head, mats["skin_pale"])
    set_smooth(head)
    parts.append(head)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.175, location=loc(Vector((0, 0.08, 1.6))))
    hair = bpy.context.active_object
    hair.name = "Szeth_Hair"
    hair.scale = (1.0, 1.0, 0.45)
    assign_material(hair, mats["hair_dark"])
    parts.append(hair)

    for side, ox in (("L", -0.18), ("R", 0.18)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.055, depth=0.62, location=loc(Vector((ox, 0.02, 1.0))))
        arm = bpy.context.active_object
        arm.name = f"Szeth_Arm_{side}"
        arm.rotation_euler = (math.radians(8), 0, math.radians(6 if side == "R" else -6))
        assign_material(arm, mats["white_fabric"])
        parts.append(arm)

    parent_parts(root, parts)

    eyes_pivot = bpy.data.objects.new("Szeth_EyesPivot", None)
    eyes_pivot.parent = head
    eyes_pivot.location = (0, 0, 0)
    bpy.context.collection.objects.link(eyes_pivot)

    for side, ox in (("L", -0.055), ("R", 0.055)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.028, location=loc(Vector((ox, 0.2, 1.53))))
        eye = bpy.context.active_object
        eye.name = f"Szeth_Eye_{side}"
        assign_material(eye, mats["eye_white"])
        eye.parent = eyes_pivot

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.014, location=loc(Vector((ox, 0.23, 1.53))))
        pupil = bpy.context.active_object
        pupil.name = f"Szeth_Pupil_{side}"
        assign_material(pupil, mats["eye_dark"])
        pupil.parent = eye

    for frame in (1, FRAME_END):
        root.keyframe_insert("location", frame=frame)
        root.keyframe_insert("rotation_euler", frame=frame)

    eyes_pivot.rotation_euler = (0, 0, 0)
    eyes_pivot.keyframe_insert("rotation_euler", frame=1)
    eyes_pivot.keyframe_insert("rotation_euler", frame=EYE_TURN_FRAME - 12)
    eyes_pivot.rotation_euler = (0, math.radians(-42), 0)
    eyes_pivot.keyframe_insert("rotation_euler", frame=EYE_TURN_FRAME)
    eyes_pivot.keyframe_insert("rotation_euler", frame=FRAME_END)

    link_to_collection(root, "Characters")
    return root


# ---------------------------------------------------------------------------
# Lighting, Volumetrics, Camera, Render
# ---------------------------------------------------------------------------

def setup_world_volumetrics() -> None:
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("FeastHallWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    vol = nodes.new("ShaderNodeVolumeScatter")
    mix = nodes.new("ShaderNodeAddShader")

    bg.inputs["Color"].default_value = (0.015, 0.01, 0.008, 1.0)
    bg.inputs["Strength"].default_value = 0.08
    vol.inputs["Color"].default_value = (0.85, 0.55, 0.25, 1.0)
    vol.inputs["Density"].default_value = 0.018
    vol.inputs["Anisotropy"].default_value = 0.35

    links.new(bg.outputs["Background"], mix.inputs[0])
    links.new(vol.outputs["Volume"], mix.inputs[1])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 6))
    vol_box = bpy.context.active_object
    vol_box.name = "GodRayVolume"
    vol_box.scale = (45, 45, 14)
    vol_box.display_type = "WIRE"
    vol_box.hide_render = True


def setup_lighting(szeth: bpy.types.Object) -> None:
    setup_world_volumetrics()

    sun = bpy.data.lights.new("GodRaySun", type="SPOT")
    sun.color = (1.0, 0.78, 0.45)
    sun.energy = 1800
    sun.spot_size = math.radians(55)
    sun.spot_blend = 0.65
    sun_obj = bpy.data.objects.new("GodRaySun", sun)
    sun_obj.location = (6, 14, 13)
    look_at(sun_obj, Vector((0, 0, 2)))
    bpy.context.collection.objects.link(sun_obj)

    cool = bpy.data.lights.new("SzethCoolShadow", type="AREA")
    cool.color = (0.5, 0.62, 0.82)
    cool.energy = 95
    cool.size = 4.0
    cool_obj = bpy.data.objects.new("SzethCoolShadow", cool)
    cool_obj.location = (-18.5, -3.5, 4.5)
    look_at(cool_obj, szeth.location + Vector((0, 0, 1.5)))
    bpy.context.collection.objects.link(cool_obj)

    rim = bpy.data.lights.new("SzethWarmRim", type="SPOT")
    rim.color = (1.0, 0.82, 0.55)
    rim.energy = 650
    rim.spot_size = math.radians(35)
    rim_obj = bpy.data.objects.new("SzethWarmRim", rim)
    rim_obj.location = (-12, -1, 3.5)
    look_at(rim_obj, szeth.location + Vector((0, 0.2, 1.5)))
    bpy.context.collection.objects.link(rim_obj)


def setup_camera(szeth: bpy.types.Object) -> bpy.types.Object:
    cam_data = bpy.data.cameras.new("FeastHallCamera")
    cam_data.lens = 32
    cam_data.clip_end = 500
    cam = bpy.data.objects.new("FeastHallCamera", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    focus = szeth.location + Vector((0.1, 0.3, 1.52))
    face = focus + Vector((0.05, 0.2, 0.02))

    keyframes = [
        (1, Vector((1, 24, 13)), Vector((0, 0, 4))),
        (60, Vector((-2, 14, 7)), Vector((-6, -2, 2))),
        (120, Vector((-12.5, -5.5, 2.6)), focus),
        (180, Vector((-14.8, -4.9, 1.78)), face),
        (FRAME_END, Vector((-15.0, -4.7, 1.72)), face),
    ]

    for frame, loc, target in keyframes:
        cam.location = loc
        look_at(cam, target)
        cam.keyframe_insert("location", frame=frame)
        cam.keyframe_insert("rotation_euler", frame=frame)

    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"

    return cam


def setup_eevee_render() -> None:
    scene = bpy.context.scene
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.fps = FPS
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.55

    eevee = scene.eevee
    if hasattr(eevee, "use_bloom"):
        eevee.use_bloom = True
        eevee.bloom_intensity = 0.08
        eevee.bloom_threshold = 0.85
    if hasattr(eevee, "use_ssr"):
        eevee.use_ssr = True
        eevee.use_ssr_refraction = True
    if hasattr(eevee, "use_gtao"):
        eevee.use_gtao = True
        eevee.gtao_distance = 1.2
    if hasattr(eevee, "use_volumetric_lights"):
        eevee.use_volumetric_lights = True
        eevee.volumetric_tile_size = "2"
        eevee.volumetric_samples = 64
        eevee.volumetric_start = 0.1
        eevee.volumetric_end = 80.0
    if hasattr(eevee, "taa_render_samples"):
        eevee.taa_render_samples = 64
    if hasattr(eevee, "taa_samples"):
        eevee.taa_samples = 8


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
    for obj in build_musicians(mats):
        link_to_collection(obj, "Characters")

    crowd = build_crowd(mats)
    link_to_collection(crowd, "Characters")

    szeth = build_szeth(mats)
    setup_lighting(szeth)
    setup_camera(szeth)
    setup_eevee_render()

    bpy.context.scene.name = "Scene01_FeastHall"
    SCENE_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(SCENE_PATH))
    print(f"Saved scene: {SCENE_PATH}")


def render_preview() -> None:
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.frame_set(PREVIEW_FRAME)
    bpy.context.scene.render.filepath = str(PREVIEW_PATH.with_suffix(""))
    bpy.ops.render.render(write_still=True)
    print(f"Rendered Eevee preview (frame {PREVIEW_FRAME}): {PREVIEW_PATH}")


def main() -> None:
    build_scene()
    render_preview()


if __name__ == "__main__":
    main()