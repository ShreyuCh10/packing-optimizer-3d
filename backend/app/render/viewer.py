import colorsys

import trimesh

from app.models import CustomBoxResult


def render_custom_box(result: CustomBoxResult) -> bytes:
    """3D scene: a transparent box with every placed item inside. Units: mm."""
    b = result.box_dimensions
    scene = trimesh.Scene()

    # trimesh boxes are centred on the origin, so shift by half the size
    # to put the minimum corner at the given position
    box = trimesh.creation.box(extents=(b.length, b.width, b.height))
    box.apply_translation((b.length / 2, b.width / 2, b.height / 2))
    box.visual.face_colors = [180, 140, 90, 60]  # low alpha = see-through
    scene.add_geometry(box, node_name="box")

    count = len(result.placements)
    for index, p in enumerate(result.placements):
        s = p.size
        mesh = trimesh.creation.box(extents=(s.length, s.width, s.height))
        mesh.apply_translation(
            (
                p.position[0] + s.length / 2,
                p.position[1] + s.width / 2,
                p.position[2] + s.height / 2,
            )
        )
        # a slightly different shade per item so layers are distinguishable
        r, g, bl = colorsys.hsv_to_rgb(0.6, 0.35 + 0.5 * index / max(count, 1), 0.9)
        mesh.visual.face_colors = [int(r * 255), int(g * 255), int(bl * 255), 255]
        scene.add_geometry(mesh, node_name=f"item_{index}")

    return scene.export(file_type="glb")