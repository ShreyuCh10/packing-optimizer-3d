
from pathlib import Path

import numpy as np
import trimesh

from app.models import CustomBoxResult


# Measurement line colours: X = Length, Y = Width, Z = Height.
LENGTH_COLOR = [220, 55, 55, 255]
WIDTH_COLOR = [35, 155, 90, 255]
HEIGHT_COLOR = [45, 105, 220, 255]

BOX_EDGE_COLOR = [45, 65, 85, 255]


def _add_line(
    scene: trimesh.Scene,
    start,
    end,
    color,
    name: str,
    radius: float = 1.5,
):
    """Add a 3D cylinder between two points."""

    start = np.asarray(start, dtype=float)
    end = np.asarray(end, dtype=float)

    direction = end - start
    length = np.linalg.norm(direction)

    if length <= 0:
        return

    midpoint = (start + end) / 2

    transform = trimesh.geometry.align_vectors(
        [0, 0, 1],
        direction / length,
    )

    transform[:3, 3] = midpoint

    line = trimesh.creation.cylinder(
        radius=radius,
        height=length,
        sections=8,
        transform=transform,
    )

    line.visual.face_colors = color

    scene.add_geometry(line, node_name=name)


def _add_box_edges(scene: trimesh.Scene, length, width, height):
    """Add visible 3D edges around the box."""

    corners = [
        (0, 0, 0),
        (length, 0, 0),
        (0, width, 0),
        (length, width, 0),
        (0, 0, height),
        (length, 0, height),
        (0, width, height),
        (length, width, height),
    ]

    edges = [
        (0, 1), (0, 2), (1, 3), (2, 3),
        (4, 5), (4, 6), (5, 7), (6, 7),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]

    for index, (first, second) in enumerate(edges):
        _add_line(
            scene,
            corners[first],
            corners[second],
            BOX_EDGE_COLOR,
            f"box_edge_{index}",
            radius=1.2,
        )


def _add_measurement_lines(
    scene: trimesh.Scene,
    length: float,
    width: float,
    height: float,
):
    """Add dimension indicators as actual 3D geometry."""

    offset = max(length, width, height) * 0.045
    tick = max(length, width, height) * 0.012

    # Length indicator (X axis).
    x_start = (0, -offset, -offset)
    x_end = (length, -offset, -offset)

    _add_line(
        scene, x_start, x_end,
        LENGTH_COLOR, "length_dimension",
        radius=2.0,
    )

    _add_line(
        scene,
        (0, -offset - tick, -offset),
        (0, -offset + tick, -offset),
        LENGTH_COLOR,
        "length_start_tick",
    )

    _add_line(
        scene,
        (length, -offset - tick, -offset),
        (length, -offset + tick, -offset),
        LENGTH_COLOR,
        "length_end_tick",
    )

    # Width indicator (Y axis).
    y_start = (-offset, 0, -offset)
    y_end = (-offset, width, -offset)

    _add_line(
        scene, y_start, y_end,
        WIDTH_COLOR, "width_dimension",
        radius=2.0,
    )

    _add_line(
        scene,
        (-offset - tick, 0, -offset),
        (-offset + tick, 0, -offset),
        WIDTH_COLOR,
        "width_start_tick",
    )

    _add_line(
        scene,
        (-offset - tick, width, -offset),
        (-offset + tick, width, -offset),
        WIDTH_COLOR,
        "width_end_tick",
    )

    # Height indicator (Z axis).
    z_start = (-offset, -offset, 0)
    z_end = (-offset, -offset, height)

    _add_line(
        scene, z_start, z_end,
        HEIGHT_COLOR, "height_dimension",
        radius=2.0,
    )

    _add_line(
        scene,
        (-offset - tick, -offset, 0),
        (-offset + tick, -offset, 0),
        HEIGHT_COLOR,
        "height_start_tick",
    )

    _add_line(
        scene,
        (-offset - tick, -offset, height),
        (-offset + tick, -offset, height),
        HEIGHT_COLOR,
        "height_end_tick",
    )


def _create_box_mesh(result: CustomBoxResult) -> trimesh.Trimesh:
    """Create the transparent outer box."""

    dimensions = result.box_dimensions

    box = trimesh.creation.box(
        extents=(
            dimensions.length,
            dimensions.width,
            dimensions.height,
        )
    )

    box.apply_translation(
        (
            dimensions.length / 2,
            dimensions.width / 2,
            dimensions.height / 2,
        )
    )

    box.visual.material = trimesh.visual.material.PBRMaterial(
        name="TransparentPackaging",
        baseColorFactor=[180, 200, 220, 35],
        metallicFactor=0.0,
        roughnessFactor=0.8,
        alphaMode="BLEND",
        doubleSided=True,
    )

    return box


def _load_product_meshes(model_path: Path):
    """
    Load product geometry while retaining the original component
    transforms and visual materials.

    Supports both single-mesh and multi-part scene files.
    """

    loaded_model = trimesh.load(
        str(model_path),
        force="scene",
        process=False,
    )

    if isinstance(loaded_model, trimesh.Trimesh):
        meshes = [loaded_model.copy()]

    elif isinstance(loaded_model, trimesh.Scene):
        meshes = [
            geometry.copy()
            for geometry in loaded_model.dump(
                concatenate=False
            )
            if isinstance(geometry, trimesh.Trimesh)
        ]

    else:
        raise ValueError(
            "Unable to load the product 3D model."
        )

    meshes = [
        mesh for mesh in meshes
        if not mesh.is_empty and len(mesh.vertices) > 0
    ]

    if not meshes:
        raise ValueError(
            "The product 3D model contains no mesh geometry."
        )

    # Calculate bounds across all components.
    all_bounds = np.array(
        [mesh.bounds for mesh in meshes],
        dtype=float,
    )

    minimum = np.min(all_bounds[:, 0, :], axis=0)
    maximum = np.max(all_bounds[:, 1, :], axis=0)

    original_size = maximum - minimum

    if (
        not np.isfinite(original_size).all()
        or (original_size <= 0).any()
    ):
        raise ValueError(
            "The product model has invalid dimensions."
        )

    # Normalize all components using the same origin.
    for mesh in meshes:
        mesh.vertices -= minimum

    return meshes, original_size


def render_empty_box(
    result: CustomBoxResult,
    show_measurements: bool = False,
) -> bytes:
    """Generate an empty transparent box with optional 3D measurements."""

    dimensions = result.box_dimensions

    scene = trimesh.Scene()

    scene.add_geometry(
        _create_box_mesh(result),
        node_name="empty_custom_box",
    )

    _add_box_edges(
        scene,
        dimensions.length,
        dimensions.width,
        dimensions.height,
    )

    if show_measurements:
        _add_measurement_lines(
            scene,
            dimensions.length,
            dimensions.width,
            dimensions.height,
        )

    return scene.export(file_type="glb")


def render_packed_box(
    result: CustomBoxResult,
    product_model_path: str | Path,
) -> bytes:
    """
    Generate a transparent box containing the actual product models.

    Original product geometry and visual materials are preserved.
    Supports single-mesh and multi-part product models.
    """

    model_path = Path(product_model_path)

    if not model_path.is_file():
        raise FileNotFoundError(
            f"Product 3D model not found: {model_path}"
        )

    if not result.placements:
        raise ValueError(
            "No product placements are available for the packed preview."
        )

    # Load all product components with their original appearance.
    original_meshes, original_size = _load_product_meshes(
        model_path
    )

    scene = trimesh.Scene()

    dimensions = result.box_dimensions

    # Add the transparent outer packaging.
    scene.add_geometry(
        _create_box_mesh(result),
        node_name="packed_custom_box",
    )

    # Add visible outer box boundaries.
    _add_box_edges(
        scene,
        dimensions.length,
        dimensions.width,
        dimensions.height,
    )

    # Add each product at its calculated placement.
    for index, placement in enumerate(result.placements):

        target_size = np.array(
            [
                placement.size.length,
                placement.size.width,
                placement.size.height,
            ],
            dtype=float,
        )

        if (
            not np.isfinite(target_size).all()
            or (target_size <= 0).any()
        ):
            raise ValueError(
                f"Invalid product dimensions in placement {index + 1}."
            )

        position = np.asarray(
            placement.position,
            dtype=float,
        )

        if not np.isfinite(position).all():
            raise ValueError(
                f"Invalid product position in placement {index + 1}."
            )

        # Apply the same scaling to every component of this product.
        scale = target_size / original_size

        for component_index, original_mesh in enumerate(original_meshes):

            product_mesh = original_mesh.copy()

            # Scale the actual product geometry.
            product_mesh.apply_scale(scale)

            # Position the complete product inside the box.
            product_mesh.apply_translation(position)

            # Keep the original material and colour.
            # Only add a neutral visual if the source has none.
            if product_mesh.visual is None:
                product_mesh.visual = trimesh.visual.ColorVisuals(
                    mesh=product_mesh,
                    face_colors=[160, 170, 185, 255],
                )

            scene.add_geometry(
                product_mesh,
                node_name=(
                    f"product_{index + 1}_component_{component_index + 1}"
                ),
            )

    return scene.export(file_type="glb")


def render_custom_box(result: CustomBoxResult) -> bytes:
    """Backward-compatible empty-box renderer."""

    return render_empty_box(result)
