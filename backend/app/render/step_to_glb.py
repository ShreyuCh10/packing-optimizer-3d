
from pathlib import Path

import trimesh

from OCP.STEPControl import STEPControl_Reader
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location


def convert_step_to_glb(step_path: str | Path) -> bytes:
    """Convert a STEP model into GLB format using OCP and trimesh."""

    step_path = Path(step_path)

    if not step_path.is_file():
        raise FileNotFoundError(
            f"STEP model not found: {step_path}"
        )

    # Read the STEP file.
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(step_path))

    if status != 1:
        raise ValueError(
            f"Unable to read STEP model: {step_path.name}"
        )

    reader.TransferRoots()
    shape = reader.OneShape()

    if shape.IsNull():
        raise ValueError(
            "STEP file contains no valid geometry."
        )

    # Convert CAD surfaces into triangles.
    mesher = BRepMesh_IncrementalMesh(shape, 0.5)
    mesher.Perform()

    vertices = []
    faces = []
    vertex_offset = 0

    explorer = TopExp_Explorer(shape, TopAbs_FACE)

    while explorer.More():
        face = TopoDS.Face(explorer.Current())
        location = TopLoc_Location()

        triangulation = BRep_Tool.Triangulation_s(
            face,
            location,
        )

        if (
            triangulation is not None
            and triangulation.NbNodes() > 0
            and triangulation.NbTriangles() > 0
        ):
            transform = location.Transformation()

            # Extract mesh vertices.
            for index in range(
                1,
                triangulation.NbNodes() + 1,
            ):
                point = triangulation.Node(index).Transformed(
                    transform
                )

                vertices.append(
                    (point.X(), point.Y(), point.Z())
                )

            # Extract triangle faces.
            reversed_face = (
                face.Orientation() == TopAbs_REVERSED
            )

            for index in range(
                1,
                triangulation.NbTriangles() + 1,
            ):
                triangle = triangulation.Triangle(index)
                a, b, c = triangle.Get()

                if reversed_face:
                    b, c = c, b

                faces.append(
                    (
                        vertex_offset + a - 1,
                        vertex_offset + b - 1,
                        vertex_offset + c - 1,
                    )
                )

            vertex_offset += triangulation.NbNodes()

        explorer.Next()

    if not vertices or not faces:
        raise ValueError(
            "STEP model could not be converted into a mesh."
        )

    # Create the final triangular mesh.
    mesh = trimesh.Trimesh(
        vertices=vertices,
        faces=faces,
        process=True,
    )

    if mesh.is_empty:
        raise ValueError(
            "Generated mesh is empty."
        )

    # Export as GLB.
    scene = trimesh.Scene(mesh)

    glb_data = scene.export(file_type="glb")

    return glb_data
