"""3D Mesh Generation & CAD Conversion Service.

Uses Python's `trimesh` (with `cascadio` OpenCASCADE bindings) to:
1. Load STEP CAD models and export them as standard web-ready GLB (glTF binary).
2. Generate procedural 3D meshes (boxes, cylinders, extrusions) for catalog products
   based on their real physical dimensions and material classifications.
3. Cache converted GLB files on disk for high performance.
"""

import os
import hashlib
from typing import Dict, Any, Optional, Tuple
import trimesh
import numpy as np

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "models", "cache")

os.makedirs(CACHE_DIR, exist_ok=True)

# Default material color palettes (RGBA 0-255)
MATERIAL_COLORS: Dict[str, Tuple[int, int, int, int]] = {
    "wood": (205, 155, 105, 255),          # Warm amber wood
    "hardwood": (185, 130, 80, 255),
    "steel": (160, 170, 185, 255),         # Industrial cool steel
    "stainless steel": (215, 220, 228, 255),
    "hardened steel": (130, 140, 155, 255),
    "cast iron": (100, 105, 115, 255),
    "tool steel": (145, 150, 160, 255),
    "sheet metal": (180, 190, 205, 255),
    "aluminum": (200, 220, 235, 255),      # Light silvery-blue
    "cast aluminum": (185, 205, 220, 255),
    "brass": (220, 175, 45, 255),          # Warm gold/brass
    "bronze": (195, 140, 50, 255),
    "copper": (210, 115, 75, 255),
    "plastic": (45, 175, 180, 255),        # Vibrant industrial teal
    "nylon": (230, 230, 220, 255),
    "pom": (240, 240, 240, 255),
    "abs": (60, 160, 170, 255),
    "polycarbonate": (190, 230, 240, 220),
    "hdpe": (225, 235, 240, 255),
    "rubber": (45, 45, 50, 255),           # Matte charcoal
    "glass": (180, 225, 245, 180),         # Translucent soft cyan
    "acrylic": (190, 235, 250, 190),
    "carbon fiber": (35, 35, 40, 255),     # Graphite black
    "default": (160, 175, 195, 255),
}


def get_material_color(material_name: Optional[str]) -> Tuple[int, int, int, int]:
    """Resolve an RGBA color based on material description."""
    m = (material_name or "").lower().strip()
    for key, color in MATERIAL_COLORS.items():
        if key in m:
            return color
    return MATERIAL_COLORS["default"]


def get_glb_for_step_file(step_rel_or_abs_path: str) -> bytes:
    """Load a STEP file using trimesh and export it as GLB binary.

    Utilizes file caching in `backend/data/models/cache/`.
    """
    if os.path.isabs(step_rel_or_abs_path):
        abs_step = step_rel_or_abs_path
    else:
        abs_step = os.path.join(DATA_DIR, step_rel_or_abs_path)
        if not os.path.exists(abs_step):
            abs_step = os.path.join(DATA_DIR, "models", os.path.basename(step_rel_or_abs_path))

    if not os.path.exists(abs_step):
        raise FileNotFoundError(f"STEP model file not found at: {abs_step}")

    # Generate a cache filename based on file mtime and size
    stat = os.stat(abs_step)
    cache_key = hashlib.md5(f"{abs_step}_{stat.st_mtime}_{stat.st_size}".encode()).hexdigest()
    base_name = os.path.splitext(os.path.basename(abs_step))[0]
    cache_file = os.path.join(CACHE_DIR, f"{base_name}_{cache_key[:8]}.glb")

    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            return f.read()

    # Load via trimesh (using cascadio under the hood for OpenCASCADE STEP geometry)
    scene_or_mesh = trimesh.load(abs_step)

    # Export to GLB
    glb_bytes = scene_or_mesh.export(file_type="glb")

    # Save to disk cache
    try:
        with open(cache_file, "wb") as f:
            f.write(glb_bytes)
    except Exception:
        pass

    return glb_bytes


def generate_procedural_mesh(
    part_name: str,
    length_mm: float,
    breadth_mm: float,
    height_mm: float,
    part_type: str = "Standard",
) -> bytes:
    """Generate a 3D procedural geometric mesh (box or cylinder) using Python's trimesh.

    Converts millimeter dimensions to scale-appropriate visual units and embeds material colors.
    """
    color = get_material_color(part_type)
    name_lower = part_name.lower()

    # Normalize dimensions in mm
    lx = max(float(length_mm), 1.0)
    ly = max(float(breadth_mm), 1.0)
    lz = max(float(height_mm), 1.0)

    # Check if part geometry is cylindrical (e.g. pin, shaft, rod, tube, standoff, washer)
    is_cylinder = (
        ("pin" in name_lower or "shaft" in name_lower or "rod" in name_lower or "tube" in name_lower or "mast" in name_lower)
        and (abs(ly - lz) < 1.0 or abs(lx - ly) < 1.0)
    )

    if is_cylinder:
        # Determine radius and height along the primary axis
        if abs(ly - lz) < 1.0:
            radius = min(ly, lz) / 2.0
            height = lx
            mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=36)
            # Orient along X axis to match length
            transform = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])
            mesh.apply_transform(transform)
        else:
            radius = min(lx, ly) / 2.0
            height = lz
            mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=36)
    else:
        # Standard Cuboid / Plate Primitive
        mesh = trimesh.creation.box(extents=[lx, ly, lz])

    # Apply material color
    mesh.visual.vertex_colors = np.full((len(mesh.vertices), 4), color, dtype=np.uint8)

    # Center mesh at origin
    mesh.apply_translation(-mesh.centroid)

    return mesh.export(file_type="glb")


def get_product_mesh_glb(product: Dict[str, Any]) -> Tuple[bytes, bool, str]:
    """Retrieve or generate GLB mesh for a product.

    Returns:
        (glb_bytes, is_cad_model, filename)
    """
    model_file = product.get("model_file")

    if model_file and str(model_file).strip():
        try:
            glb = get_glb_for_step_file(str(model_file).strip())
            return glb, True, os.path.basename(str(model_file))
        except Exception as e:
            print(f"[Warning] Failed to load CAD STEP file '{model_file}': {e}. Falling back to procedural mesh.")

    # Procedural mesh fallback generated by trimesh
    glb = generate_procedural_mesh(
        part_name=product.get("part_name", "Part"),
        length_mm=float(product.get("part_length", 100.0)),
        breadth_mm=float(product.get("part_breadth", 100.0)),
        height_mm=float(product.get("part_height", 100.0)),
        part_type=str(product.get("part_type", "Standard")),
    )
    return glb, False, f"{product.get('part_name', 'product')}.glb"
