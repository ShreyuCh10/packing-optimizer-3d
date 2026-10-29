from typing import List, Tuple


def get_possible_orientations(
    length: float,
    width: float,
    height: float,
    allow_rotation: bool = True,
    keep_upright: bool = False,
) -> List[Tuple[float, float, float]]:
    """Generate distinct 3D orthogonal bounding box orientations."""
    if not allow_rotation:
        return [(length, width, height)]

    if keep_upright:
        # Only allow 90-degree yaw rotation around vertical Z axis (height fixed)
        orientations = {(length, width, height), (width, length, height)}
        return list(orientations)

    # All 6 full 3D orthogonal permutations
    all_perms = {
        (length, width, height),
        (length, height, width),
        (width, length, height),
        (width, height, length),
        (height, length, width),
        (height, width, length),
    }
    return list(all_perms)

