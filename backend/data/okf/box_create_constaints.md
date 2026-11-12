# Box creation constraints

Use these rules when creating or evaluating a box for one product or a group of products. Dimensions are in millimetres and weights are in kilograms unless stated otherwise. This document intentionally distinguishes repository defaults from general decision guidance.

## 1. Required inputs

Before sizing, collect as much of the following as is available:

- Product count and dimensions (length × breadth/width × height) for each distinct item.
- Unit and total product weight; use the heaviest credible value if weight varies.
- Allowed orientation and any keep-upright, no-stack, load-bearing, or handling restrictions.
- Product material/category, fragility, surface sensitivity, and known compatibility hazards.
- Required cushioning, separation, moisture/ESD protection, or other validated packaging specification.
- Available box materials, their rated payload/gross capacity, wall thickness, inner dimensions, and supplier limits.
- Destination, shipping mode, carrier limits, and whether freight is acceptable.

Missing data must stay marked **unknown**. In particular, do not infer that a product can bear stacking load, that two materials are chemically compatible, or that a packaging material is moisture/ESD safe.

## 2. Product envelope and dimensions

1. Validate all product dimensions as positive and weight as non-negative. The application currently rejects dimensions over 5000 mm; this is an input-validation ceiling, not a recommended carton size.
2. Consider only allowed 90-degree orientations. Rotation must not violate an upright, grain, connector, fluid, or other product constraint. If no orientation rule is supplied, ask the packing solver to test its supported orientations and disclose the assumption.
3. For one item, start with its oriented dimensions. For multiple items, use a verified 3D layout or packing result; do not simply add lengths or divide volume and assume a fit.
4. Add separators/dividers where contact, abrasion, entanglement, or part-to-part impact is a concern. The code's multi-unit layout uses a 3 mm divider default; validate or override it for the actual material and design.
5. The dimensions returned by the packing plan must fit the **internal** box dimensions, including the complete protective package. Do not compare bare-product dimensions with external dimensions.

### Clearance and cushioning defaults in this project

`backend/data/padding_rules.json` contains these current starting values. They are defaults for recommendations, not proof of a drop-test rating:

| Product type | Suggested protection | Thickness per side | Minimum clearance | Configured fragility |
|---|---|---:|---:|---|
| Glass | EPE foam | 35 mm | 10 mm | High |
| Electronics | ESD anti-static foam | 25 mm | 8 mm | High |
| Steel | Dense EVA foam | 20 mm | 5 mm | Medium |
| Aluminum | Polyethylene foam | 15 mm | 5 mm | Medium |
| Plastic | Bubble wrap | 12 mm | 5 mm | Low |
| Wood | Corrugated cushion | 10 mm | 5 mm | Low |
| Standard/unknown match | Kraft paper cushion | 10 mm | 5 mm | Low |
| Fallback for unmatched type | EPE foam | 15 mm | 5 mm | Medium |

The sizing service adds padding thickness on both opposite faces: `internal dimension = protected content dimension + 2 × padding thickness`. It separately adds wall thickness on both faces for external dimensions. Use the more protective documented requirement if product/customer instructions require more than this default. “Unknown” or non-matching product categories should be treated conservatively and reviewed rather than assumed safe from a fuzzy category match.

For multiple independently protected products, account for cushioning between neighbouring products as well as around the outer perimeter. A single outer padding allowance does not create internal separation.

## 3. Material selection and capacity

Current entries in `backend/data/materials.json`:

| Configured material | Wall thickness | Configured maximum weight | Density estimate | Cost estimate |
|---|---:|---:|---:|---:|
| Single-wall corrugated cardboard (ECT 32) | 4 mm | 15 kg | 120 kg/m³ | 1.20 / m² |
| Double-wall heavy-duty cardboard (ECT 48) | 7 mm | 35 kg | 180 kg/m³ | 2.50 / m² |
| Triple-wall industrial cardboard (ECT 71) | 12 mm | 75 kg | 250 kg/m³ | 4.80 / m² |
| Polypropylene fluted plastic | 5 mm | 25 kg | 160 kg/m³ | 3.40 / m² |
| Plywood/wood reinforced crate | 18 mm | 250 kg | 600 kg/m³ | 12.00 / m² |

Treat these maximum weights as configured screening limits only. Confirm from the supplier whether each rating is payload or gross weight and whether it applies to the actual box dimensions, stacking, moisture, closures, and handling. Until clarified, use the conservative interpretation: **gross package weight must not exceed the configured maximum**. Include product, box, cushioning, dividers, and accessories when calculating gross weight.

Selection rules:

- Choose the lightest/lowest-cost candidate that passes all size, protection, and weight checks with an adequate verified margin; never choose by cost alone.
- Increase structural strength for heavy contents, high compression/stacking loads, large unsupported spans, long narrow boxes, or rough handling. Use a crate or freight design when carton limits are insufficient, subject to engineering approval.
- Match protection to the product: ESD-safe packaging for ESD-sensitive electronics, cushioning for impact-sensitive items, and validated moisture/chemical barriers where required.
- Separate hard, sharp, oily, dirty, abrasive, or heavy items from soft/fragile items. Prevent a heavier item from bearing on a fragile item unless the latter's compression rating is known and sufficient.
- Do not claim material compatibility, waterproofing, food safety, anti-static performance, or load-bearing capacity unless the candidate data explicitly supports it.

## 4. Size, weight, and carrier checks

The current custom-box constraint code defaults to:

- Material maximum weight: 35 kg (overridable; select the applicable material rating instead of blindly using this default).
- Standard parcel gross-weight threshold: 70 kg; above it the configured check reports freight required.
- Longest external dimension: 2740 mm maximum.
- Longest dimension + girth: 4000 mm maximum, where girth is twice the sum of the other two external dimensions.
- Longest-to-shortest external dimension ratio above 5:1: warning for bending/crush risk, not a confirmed carrier rejection.

These are application defaults. Carrier contracts and destination rules vary; verify current applicable limits. Freight classification, fees, and handling are not established by these checks.

There is no universal rule that a given product length maps to a fixed box breadth or height. Derive all three internal dimensions from the packed, protected geometry, then derive all three external dimensions from actual wall construction. A long product may require a long box, but its width and height depend on its cross-section, orientation, protection, and fit. Check the final external dimensions against carrier limits.

## 5. Feasibility checklist

Do not call a box feasible until all applicable checks pass:

- Every item is placed by a 3D packing check inside the usable internal dimensions.
- Product orientation and upright restrictions are respected.
- Padding, dividers, and required separation are included in the packed geometry.
- Gross weight is within the applicable verified box capacity and shipping-mode limit.
- External dimensions pass the selected carrier/service limits, or the shipment is explicitly routed to an appropriate freight option.
- Fragile items cannot be crushed by heavier items; load-bearing assumptions are supported by data.
- Material/protection needs are satisfied or clearly flagged for human verification.
- Any warnings (for example, a high aspect ratio) are surfaced with the recommendation.

If no candidate passes, record each failure (dimension, weight, orientation, protection, or missing rating), then evaluate a different material, engineered container, freight option, or safe multi-box split. Never label a partial fit as a complete solution.
