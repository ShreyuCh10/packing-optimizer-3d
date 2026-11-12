# Multi-box rules

Use these rules to decide whether a requested quantity should ship in one package or be split. A split is valid only when each resulting package is independently feasible and the split preserves product safety and order requirements.

## 1. Decision order

1. **Establish the shipment constraints.** Gather item quantities and dimensions, unit weights, orientation restrictions, protection requirements, delivery/order grouping requirements, available box candidates, and carrier/service limits.
2. **Try a single package.** Use a 3D packing solver against actual internal dimensions and allowed orientations. Include cushioning, dividers, and handling constraints. Check the applicable gross/payload rating and external shipping limits.
3. **Accept one box only if all contents fit and all hard checks pass.** High volume utilization is not a substitute for verified fit or protection. Prefer one box when it is safe, operationally sensible, and materially more efficient.
4. **If no single box passes, test a split.** Split by quantity, product type, weight, geometry, fragility, or handling group as appropriate. Verify every proposed box independently.
5. **Compare feasible options.** Among safe choices, consider number of boxes, protection, confirmed weight margin, wasted volume, handling complexity, and cost/shipping constraints. Report the trade-offs and assumptions.
6. **If no verified split passes, stop.** State the specific missing data or limiting constraints and request an engineered/freight solution. Do not pretend the items fit.

## 2. Reasons to split

Split is required or strongly preferred when one package would:

- Exceed a verified box material/payload rating, carrier parcel weight limit, longest-edge limit, or length-plus-girth limit.
- Fail 3D placement in every allowed orientation, including required protective packaging.
- Need an unsafe amount of compression, bending, overhang, or stacking load to fit.
- Place heavy parts against fragile parts or make fragile products carry unknown loads.
- Mix products that need incompatible handling, ESD/moisture control, cleanliness, temperature, chemical separation, or orientation.
- Make a long or awkward package structurally risky (including a configured aspect-ratio warning) when a shorter, supported split is feasible.
- Make products difficult to identify, count, access, or deliver under the order's handling requirements.
- Violate customer requirements such as maximum units per box, lot separation, or individual protection.

Weight alone is not enough to justify a split if a correctly rated and dimensionally suitable package is verified; likewise, low weight does not make an oversize or poorly protected package safe.

## 3. How to form a split

- Keep identical product units together where that improves protection and countability, unless it causes a capacity or fit failure.
- Group products with compatible dimensions, fragility, material/protection needs, and handling requirements.
- Put heavy or dense items in a structurally suitable package with load distributed and restrained. Keep them separate from crush-sensitive products unless verified separators and compression ratings make co-packing safe.
- Give fragile products their required cushioning and prevent item-to-item contact. Use separate boxes when a divider cannot reliably isolate them.
- Split repeated units into integer quantities. Do not fractionalize a product or omit any requested unit.
- Prefer balanced boxes only after safety constraints are met. Equal weight or equal count is not inherently safer than a geometry- or fragility-based grouping.
- Avoid unnecessary splits that add handling, shipment cost, or delivery risk when a single verified package is safe.

## 4. When no single candidate fits

If no available box fits the full order:

1. Determine why each promising candidate failed: geometry, weight rating, orientation, protection allowance, or shipping limit.
2. Test combinations of smaller quantities in multiple boxes. Re-run packing and weight checks for each box; dividing total volume or total weight evenly is only a way to propose groups, not evidence of fit.
3. Search other documented package sizes/materials or an approved custom/crate design if those are within scope.
4. Check if freight shipping resolves a parcel-carrier limit. Freight does **not** resolve insufficient box strength, unsafe internal fit, or inadequate product protection.
5. If no safe plan can be proven, return “no verified package plan” with the failed constraints and required next data. Do not silently drop units, change orientation rules, lower cushioning, or exceed a rating.

## 5. Choosing among feasible plans

Apply priorities in this order:

1. Complete containment and product safety.
2. Compliance with confirmed material, weight, dimension, carrier, and customer constraints.
3. Appropriate verified protection and sensible weight margin.
4. Fewer boxes and simpler handling, where the safety difference is negligible.
5. Better use of space/lower unoccupied volume.
6. Lower documented packaging and shipping cost.

Only compare costs when the relevant rates and package attributes are available. If the box material, wall construction, handling performance, or carrier rate is unknown, say so; do not fabricate a cost or safety advantage.

## 6. Required result summary

For an AI-generated recommendation, report:

- Whether one box or multiple boxes are recommended, with the reason.
- Number of boxes and exact products/quantities assigned to each.
- The verified internal and external dimensions, gross weight, and applicable capacity/limit for each box, when available.
- Protection, orientation, and separation assumptions.
- Packing/constraint check result and remaining warnings.
- Any unknown rating or unverified requirement that needs confirmation.

An AI recommendation is a decision aid. A missing engineering or carrier rating remains unknown until authoritative data is supplied.
