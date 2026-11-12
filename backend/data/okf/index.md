# OKF — Operational Knowledge for Packaging

This folder is the packaging decision knowledge base. Read the relevant topic before proposing a custom box or deciding whether an order should be split.

## Documents

- [Box creation constraints](box_create_constaints.md): derive usable dimensions, select material and protection, and validate physical and shipping limits.
- [Multi-box rules](multi_box_rules.md): decide whether to pack an order together or split it into multiple packages.

## How to use this knowledge

1. Treat measured product/package data and configured project data as evidence. Never invent missing dimensions, weight ratings, material properties, or handling limits.
2. Separate **hard constraints** (a confirmed fit, capacity rating, or applicable carrier limit) from **recommendations** (fragility protection, margins, and economical choices).
3. A candidate is feasible only after every item fits in 3D in an allowed orientation, all required clearance/protection fits, and its applicable gross/payload limit is respected.
4. If no documented candidate is safe, report what failed and request engineering/carrier data or recommend a reviewed split. Do not silently relax a hard constraint.

The values below reflect this repository's current configuration where indicated. They are not universal packaging certifications; update them when authoritative supplier, product, or carrier specifications change.
