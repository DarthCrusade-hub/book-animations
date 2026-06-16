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
PREVIEW_FRAME = 120

try:
    import bpy
    from mathutils import Vector
except ImportError as exc:
    raise SystemExit("Run inside Blender.") from exc

SZETH_PILLAR_POS = Vector((-15.0, -3.8, 0.0))


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


def add_part(
    root: bpy.types.Object,
    name: str,
    primitive: str,
    location: Vector,
    mat: bpy.types.Material,
    scale: Vector | None = None,
    rotation: tuple[float, float, float] | None = None,
) -> bpy.types.Object:
    world_loc = root.matrix_world.translation + location
    if primitive == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=world_loc)
    elif primitive == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=1.0, location=world_loc)
    elif primitive == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=world_loc)
    elif primitive == "torus":
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.2, location=world_loc)
    else:
        raise ValueError(primitive)

    obj = bpy.context.active_object
    obj.name = name
    if scale:
        obj.scale = scale
    if rotation:
        obj.rotation_euler = rotation
    assign_material(obj, mat)
    set_smooth(obj)
    obj.parent = root
    obj.matrix_parent_inverse = root.matrix_world.inverted()
    return obj


def animate_flicker(obj: bpy.types.Object, seed: int) -> None:
    base = obj.scale.copy()
    for frame in range(1, FRAME_END + 1, 8):
        flicker = 0.85 + ((seed * 17 + frame * 13) % 30) / 100.0
        obj.scale = (base.x * flicker, base.y * flicker, base.z * (flicker + 0.08))
        obj.keyframe_insert("scale", frame=frame)


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

    for ring_i, z in enumerate([3.8, 5.8, 7.8, 9.6]):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=1.3 + ring_i * 0.015,
            minor_radius=0.11,
            location=(x, y, z),
            rotation=(math.pi / 2, 0, ring_i * 0.55),
        )
        ring = bpy.context.active_object
        ring.name = f"DragonScaleRing_{idx:02d}_{ring_i}"
        assign_material(ring, mats["gold"])
        parts.append(ring)

    for seg in range(8):
        angle = seg * 0.75
        z = 3.5 + seg * 0.95
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.2,
            location=(x + math.cos(angle) * 1.18, y + math.sin(angle) * 1.18, z),
        )
        body = bpy.context.active_object
        body.name = f"DragonCoil_{idx:02d}_{seg}"
        body.scale = (1.8, 0.65, 0.6)
        assign_material(body, mats["gold"])
        parts.append(body)

    # Dragon head crest at top of pillar
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(x + 1.1, y, 10.8))
    head = bpy.context.active_object
    head.name = f"DragonHead_{idx:02d}"
    head.scale = (1.4, 0.8, 0.75)
    assign_material(head, mats["gold"])
    parts.append(head)

    for horn_i, rz in enumerate((-0.5, 0.5)):
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.08, radius2=0.02, depth=0.45,
            location=(x + 1.25, y + (0.15 if horn_i else -0.15), 11.2),
        )
        horn = bpy.context.active_object
        horn.name = f"DragonHorn_{idx:02d}_{horn_i}"
        horn.rotation_euler = (math.radians(25), 0, rz)
        assign_material(horn, mats["gold"])
        parts.append(horn)

    for claw_i in range(3):
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.05, radius2=0.01, depth=0.3,
            location=(x + 0.9 + claw_i * 0.12, y, 10.4),
        )
        claw = bpy.context.active_object
        claw.name = f"DragonClaw_{idx:02d}_{claw_i}"
        claw.rotation_euler = (math.radians(70), 0, 0)
        assign_material(claw, mats["gold"])
        parts.append(claw)

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
        animate_flicker(flame, idx * 10 + arm_i)
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

        bpy.ops.mesh.primitive_torus_add(
            major_radius=1.82, minor_radius=0.045,
            location=(x, y, 0.91), rotation=(math.pi / 2, 0, 0),
        )
        trim = bpy.context.active_object
        trim.name = f"TableGoldTrim_{idx:02d}"
        assign_material(trim, mats["gold"])
        objects.append(trim)

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
        animate_flicker(tc_flame, idx + 200)
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
        (-5.0, "Erhu"),
        (-2.5, "Harp"),
        (0.0, "Drum"),
        (2.5, "Flute"),
        (5.0, "Zither"),
    ]
    for i, (x, kind) in enumerate(configs):
        root = bpy.data.objects.new(f"Musician_{i}_{kind}", None)
        root.location = (x, -17.2, 1.15)
        root.rotation_euler = (0, math.radians(180), 0)
        bpy.context.collection.objects.link(root)

        head = add_part(root, f"MusicianHead_{i}", "sphere", Vector((0, 0, 0.62)), mats["skin_noble"], Vector((0.2, 0.2, 0.22)))
        add_part(root, f"MusicianTorso_{i}", "cylinder", Vector((0, 0, 0.25)), mats["noble_red"], Vector((0.24, 0.24, 0.28)))
        add_part(root, f"MusicianRobe_{i}", "cylinder", Vector((0, 0, -0.05)), mats["noble_gold"], Vector((0.32, 0.32, 0.18)))
        add_part(root, f"MusicianCollar_{i}", "torus", Vector((0, 0, 0.42)), mats["gold"], Vector((0.22, 0.22, 0.06)), (math.pi / 2, 0, 0))

        if kind == "Erhu":
            add_part(root, f"Inst_{i}", "cylinder", Vector((0.15, 0.2, 0.35)), mats["wood"], Vector((0.03, 0.03, 0.5)))
            add_part(root, f"InstBow_{i}", "cube", Vector((0.25, 0.15, 0.4)), mats["wood"], Vector((0.02, 0.35, 0.02)))
        elif kind == "Drum":
            add_part(root, f"Inst_{i}", "cylinder", Vector((0, 0.25, 0.1)), mats["wood"], Vector((0.22, 0.22, 0.1)))
        elif kind == "Harp":
            add_part(root, f"Inst_{i}", "cube", Vector((0.2, 0.15, 0.35)), mats["gold"], Vector((0.08, 0.35, 0.55)))
        elif kind == "Flute":
            add_part(root, f"Inst_{i}", "cylinder", Vector((0.1, 0.22, 0.45)), mats["gold"], Vector((0.025, 0.025, 0.35)))
        else:
            add_part(root, f"Inst_{i}", "cube", Vector((0.15, 0.2, 0.3)), mats["wood"], Vector((0.25, 0.08, 0.04)))

        for frame, rz, arm in ((1, 0, 0), (30, 5, 15), (60, -4, -10), (90, 8, 20), (120, -3, -8), (150, 6, 12), (180, -5, -15), (210, 4, 8), (240, 0, 0)):
            root.rotation_euler = (0, math.radians(180), math.radians(rz))
            root.keyframe_insert("rotation_euler", frame=frame)
            head.rotation_euler = (math.radians(arm * 0.3), 0, math.radians(arm))
            head.keyframe_insert("rotation_euler", frame=frame)

        musicians.append(root)
    return musicians


def build_noble(name: str, x: float, y: float, mats: dict, seed: int) -> bpy.types.Object:
    root = bpy.data.objects.new(name, None)
    root.location = (x, y, 0)
    angle = (seed * 41) % 360
    root.rotation_euler = (0, 0, math.radians(angle))
    bpy.context.collection.objects.link(root)

    is_red = seed % 2 == 0
    robe = mats["noble_red"] if is_red else mats["noble_gold"]
    trim = mats["noble_gold"] if is_red else mats["noble_red"]

    head = add_part(root, f"{name}_Head", "sphere", Vector((0, 0, 1.52)), mats["skin_noble"], Vector((0.2, 0.2, 0.22)))
    add_part(root, f"{name}_Torso", "cylinder", Vector((0, 0, 1.05)), robe, Vector((0.26, 0.26, 0.38)))
    add_part(root, f"{name}_Skirt", "cylinder", Vector((0, 0, 0.52)), trim, Vector((0.32, 0.32, 0.22)))
    add_part(root, f"{name}_Collar", "torus", Vector((0, 0, 1.28)), mats["gold"], Vector((0.24, 0.24, 0.05)), (math.pi / 2, 0, 0))
    add_part(root, f"{name}_Sash", "torus", Vector((0, 0, 0.78)), mats["gold"], Vector((0.28, 0.28, 0.04)), (math.pi / 2, 0, 0))

    cup = add_part(root, f"{name}_Cup", "cylinder", Vector((0.22, 0.12, 1.0)), mats["gold"], Vector((0.05, 0.05, 0.08)))

    arms: list[bpy.types.Object] = []
    for side, ox in (("L", -0.28), ("R", 0.28)):
        arm = add_part(root, f"{name}_Arm_{side}", "cylinder", Vector((ox, 0, 1.0)), robe, Vector((0.07, 0.07, 0.28)))
        arm.rotation_euler = (math.radians(70), 0, math.radians(18 if side == "R" else -18))
        arms.append(arm)

    base_loc = root.location.copy()
    eating = seed % 3 == 0
    talking = seed % 3 == 1

    for frame, dz, head_turn, body_turn in (
        (1, 0.0, 0, 0),
        (30, 0.04, 14, 5),
        (60, 0.0, -10, -4),
        (90, 0.05, 18, 7),
        (120, 0.0, -8, -3),
        (150, 0.04, 12, 6),
        (180, 0.0, -12, -5),
        (210, 0.05, 9, 4),
        (240, 0.0, 0, 0),
    ):
        root.location = (base_loc.x, base_loc.y, base_loc.z + dz)
        root.rotation_euler = (0, 0, math.radians(angle + body_turn))
        root.keyframe_insert("location", frame=frame)
        root.keyframe_insert("rotation_euler", frame=frame)
        head.rotation_euler = (0, 0, math.radians(head_turn))
        head.keyframe_insert("rotation_euler", frame=frame)

        for ai, arm in enumerate(arms):
            if eating and ai == 0:
                eat_angle = 55 if frame in (45, 90, 135, 180) else 75
                arm.rotation_euler = (math.radians(eat_angle), math.radians(25), math.radians(18))
            elif talking and ai == 1:
                talk_angle = 40 if frame in (30, 90, 150, 210) else 65
                arm.rotation_euler = (math.radians(talk_angle), 0, math.radians(-18))
            else:
                wave = 70 + (10 if frame % 60 < 30 else -8)
                arm.rotation_euler = (math.radians(wave), 0, math.radians(18 if ai else -18))
            arm.keyframe_insert("rotation_euler", frame=frame)

    return root


def build_crowd(mats: dict[str, bpy.types.Material]) -> bpy.types.Object:
    crowd_root = bpy.data.objects.new("Crowd", None)
    bpy.context.collection.objects.link(crowd_root)
    seed = 0
    for y in range(-12, 13, 2):
        for x in range(-12, 13, 2):
            if abs(x) < 3 and abs(y) < 3:
                continue
            if x < -12 and -9 < y < 3:
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
    """Detailed pale young man leaning against the left dragon pillar."""
    root = bpy.data.objects.new("SZETH", None)
    root.location = (SZETH_PILLAR_POS.x - 0.85, SZETH_PILLAR_POS.y, 0)
    root.rotation_euler = (0, 0, math.radians(95))
    bpy.context.collection.objects.link(root)

    # Athletic legs
    for side, ox in (("L", -0.09), ("R", 0.09)):
        add_part(root, f"Szeth_Thigh_{side}", "cylinder", Vector((ox, 0.02, 0.55)), mats["white_fabric"], Vector((0.09, 0.09, 0.28)))
        add_part(root, f"Szeth_Calf_{side}", "cylinder", Vector((ox, 0.04, 0.18)), mats["white_fabric"], Vector((0.075, 0.075, 0.3)))
        add_part(root, f"Szeth_Foot_{side}", "cube", Vector((ox, 0.08, 0.02)), mats["white_fabric"], Vector((0.08, 0.18, 0.05)))

    # Lean athletic torso + white tunic layers
    add_part(root, "Szeth_Pelvis", "cube", Vector((0, 0.02, 0.72)), mats["white_fabric"], Vector((0.22, 0.16, 0.14)))
    torso = add_part(root, "Szeth_Torso", "cylinder", Vector((0, 0.04, 1.02)), mats["white_fabric"], Vector((0.17, 0.14, 0.34)))
    add_part(root, "Szeth_Chest", "cube", Vector((0, 0.06, 1.2)), mats["white_fabric"], Vector((0.2, 0.12, 0.18)))
    add_part(root, "Szeth_Shoulder_L", "sphere", Vector((-0.17, 0.04, 1.28)), mats["white_fabric"], Vector((0.08, 0.08, 0.08)))
    add_part(root, "Szeth_Shoulder_R", "sphere", Vector((0.17, 0.04, 1.28)), mats["white_fabric"], Vector((0.08, 0.08, 0.08)))

    # Wrapped waist cloth (layered)
    add_part(root, "Szeth_WaistWrap_A", "torus", Vector((0, 0.03, 0.82)), mats["white_fabric"], Vector((0.22, 0.22, 0.07)), (math.pi / 2, 0, 0))
    add_part(root, "Szeth_WaistWrap_B", "torus", Vector((0, 0.05, 0.78)), mats["white_fabric"], Vector((0.24, 0.24, 0.05)), (math.pi / 2, 0, 0.3))
    add_part(root, "Szeth_SashTail", "cube", Vector((0.08, 0.06, 0.7)), mats["white_fabric"], Vector((0.06, 0.22, 0.04)))

    # Arms at rest — motionless
    for side, ox in (("L", -0.2), ("R", 0.2)):
        upper = add_part(root, f"Szeth_UpperArm_{side}", "cylinder", Vector((ox, 0.02, 1.05)), mats["white_fabric"], Vector((0.055, 0.055, 0.22)))
        upper.rotation_euler = (math.radians(6), 0, math.radians(4 if side == "R" else -4))
        fore = add_part(root, f"Szeth_Forearm_{side}", "cylinder", Vector((ox, 0.04, 0.78)), mats["white_fabric"], Vector((0.045, 0.045, 0.2)))
        fore.rotation_euler = (math.radians(4), 0, 0)
        add_part(root, f"Szeth_Hand_{side}", "cube", Vector((ox, 0.05, 0.64)), mats["skin_pale"], Vector((0.05, 0.08, 0.03)))

    # Neck + expressionless face
    neck = add_part(root, "Szeth_Neck", "cylinder", Vector((0, 0.06, 1.4)), mats["skin_pale"], Vector((0.05, 0.05, 0.1)))
    head = add_part(root, "Szeth_Head", "sphere", Vector((0, 0.08, 1.56)), mats["skin_pale"], Vector((0.16, 0.18, 0.2)))
    add_part(root, "Szeth_Jaw", "cube", Vector((0, 0.1, 1.48)), mats["skin_pale"], Vector((0.12, 0.1, 0.08)))
    add_part(root, "Szeth_Brow", "cube", Vector((0, 0.14, 1.62)), mats["skin_pale"], Vector((0.14, 0.04, 0.03)))
    add_part(root, "Szeth_Nose", "cube", Vector((0, 0.16, 1.55)), mats["skin_pale"], Vector((0.025, 0.04, 0.03)))

    # Short dark hair
    add_part(root, "Szeth_HairTop", "sphere", Vector((0, 0.04, 1.66)), mats["hair_dark"], Vector((0.17, 0.17, 0.1)))
    add_part(root, "Szeth_HairSide_L", "cube", Vector((-0.1, 0.06, 1.58)), mats["hair_dark"], Vector((0.04, 0.06, 0.08)))
    add_part(root, "Szeth_HairSide_R", "cube", Vector((0.1, 0.06, 1.58)), mats["hair_dark"], Vector((0.04, 0.06, 0.08)))

    # Eye rig — slow turn toward camera at 6 seconds
    eyes_pivot = bpy.data.objects.new("Szeth_EyesPivot", None)
    eyes_pivot.parent = head
    eyes_pivot.location = (0, 0, 0)
    bpy.context.collection.objects.link(eyes_pivot)

    bpy.context.view_layer.update()
    for side, ox in (("L", -0.045), ("R", 0.045)):
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.028, location=head.matrix_world @ Vector((ox, 0.1, 0.02))
        )
        eye = bpy.context.active_object
        eye.name = f"Szeth_Eye_{side}"
        eye.scale = (1.0, 1.0, 0.75)
        assign_material(eye, mats["eye_white"])
        eye.parent = eyes_pivot
        eye.location = Vector((ox, 0.1, 0.02))

        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.012, location=head.matrix_world @ Vector((ox, 0.13, 0.02))
        )
        pupil = bpy.context.active_object
        pupil.name = f"Szeth_Pupil_{side}"
        assign_material(pupil, mats["eye_dark"])
        pupil.parent = eye
        pupil.location = Vector((0, 0.03, 0))

    # Lock Szeth completely motionless
    for frame in (1, FRAME_END):
        root.keyframe_insert("location", frame=frame)
        root.keyframe_insert("rotation_euler", frame=frame)

    eyes_pivot.rotation_euler = (0, 0, 0)
    eyes_pivot.keyframe_insert("rotation_euler", frame=1)
    eyes_pivot.keyframe_insert("rotation_euler", frame=EYE_TURN_FRAME - 24)
    eyes_pivot.rotation_euler = (0, math.radians(-48), 0)
    eyes_pivot.keyframe_insert("rotation_euler", frame=EYE_TURN_FRAME)
    eyes_pivot.keyframe_insert("rotation_euler", frame=FRAME_END)
    if eyes_pivot.animation_data and eyes_pivot.animation_data.action:
        for fc in eyes_pivot.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"

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
    vol.inputs["Density"].default_value = 0.028
    vol.inputs["Anisotropy"].default_value = 0.45

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
    sun.energy = 2400
    sun.spot_size = math.radians(55)
    sun.spot_blend = 0.65
    sun_obj = bpy.data.objects.new("GodRaySun", sun)
    sun_obj.location = (6, 14, 13)
    look_at(sun_obj, Vector((0, 0, 2)))
    bpy.context.collection.objects.link(sun_obj)

    cool = bpy.data.lights.new("SzethCoolShadow", type="AREA")
    cool.color = (0.5, 0.62, 0.82)
    cool.energy = 140
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
        (1, Vector((2, 26, 14)), Vector((0, -2, 3))),
        (40, Vector((0, 20, 10)), Vector((-4, 0, 2.5))),
        (80, Vector((-4, 12, 6)), Vector((-8, -2, 2))),
        (120, Vector((-12.0, -5.2, 2.55)), focus),
        (160, Vector((-14.2, -4.95, 1.95)), focus + Vector((0, 0.1, 0.1))),
        (200, Vector((-15.1, -4.75, 1.76)), face),
        (FRAME_END, Vector((-15.25, -4.55, 1.7)), face),
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
    scene.view_settings.exposure = 0.62

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