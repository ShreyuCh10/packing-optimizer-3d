# 3D Packing Optimizer: Workflow Test Prompts

A curated collection of natural language prompts to test and demonstrate all stages of the **3-Agent Packaging Workflow** (Requirement Gathering Agent $\rightarrow$ Retrieval & Gathering Agent $\rightarrow$ 3D Extreme Point Packing Optimizer) connected to the Chatbot.

---

## Quick Reference: Testing Matrix

| Scenario Category | Primary Agent Tested | Expected Workflow Behavior |
| :--- | :--- | :--- |
| **1. Standard Natural Language** | End-to-End Pipeline | Extracts specs, queries cartons, solves 3D Extreme Point packing. |
| **2. Database Auto-Lookup** | Retrieval Agent (SQLite) | Resolves CAD dimensions & SNP from `products` table automatically. |
| **3. Heavy Industrial Payload** | Retrieval Filtering | Exceeds 9kg carton limit $\rightarrow$ routes to `metal_stillages` (1,200kg). |
| **4. Incomplete Specification** | Requirement Agent (HITL) | Detects missing attributes $\rightarrow$ pauses and prompts for clarification. |
| **5. Fragile & Padding Rules** | Cushioning Calculations | Detects fragility $\rightarrow$ calculates thicker protective foam clearance. |
| **6. Bulk High-Density Stacking** | 3D Packing Optimizer | Packs 30+ units using 3D Extreme Points with 0 collisions. |
| **7. Oversized / Partial Fit** | Boundary Enforcement | Detects when items exceed warehouse packages $\rightarrow$ advises custom box. |

---

## 1. Standard Physical Specifications (Carton Inventory)

These prompts test end-to-end extraction from unstructured text with explicit length, width, height, weight, and quantity.

```text
Find a suitable inventory package for 4 steel brackets measuring 140x90x60mm with weight 1.2kg each.
```
- **Expected Outcome:** 
  - Extracted: Length 140mm, Width 90mm, Height 60mm, Weight 1.2kg, SNP: 4.
  - Padding: 15mm Polyethylene Foam.
  - Winner: `Package 12` (Carton).
  - Utilization: ~24% with 4/4 items placed.

```text
I need to pack 6 units of aluminum junction boxes. Each unit is 160mm long, 100mm wide, 75mm tall, and weighs 0.85kg.
```

```text
Please find an optimal shipping carton for 8 industrial sensor housings measuring 110x70x45mm and weighing 0.4kg per unit.
```

```text
Calculate the best container and orientation for packing 12 machined brass bushings: 80x50x50mm, 0.6kg each.
```

---

## 2. SQLite Database Catalog Auto-Lookup

These prompts reference parts already cataloged in the SQLite database (`backend/data/products.db`). The workflow automatically resolves part dimensions, single weight, catalog SNP, and CAD model.

```text
Lookup product 1 and pack all units according to its catalog SNP.
```
- **Expected Outcome:**
  - Auto-resolves: **Micro Terminal Block** (Product ID 1), Dimensions: 28×18×14 mm, SNP: 64 units.
  - Winner: `Package 1` (Carton).
  - 3D Viewer: Renders all 64 items packed in high-density grid.

```text
Find packaging for product id 10.
```
- **Expected Outcome:** Auto-resolves Product 10 attributes, padding, and best carton fit.

```text
Pack 16 units of Product 25 from our database catalog.
```

```text
Can you retrieve the specifications for "Micro Terminal Block" and pack a standard batch?
```

---

## 3. Heavy Industrial Payloads (> 9.0 kg)

Standard cardboard cartons (`packages` table) have a maximum payload capacity of **9.0 kg** (`Package 41`). When payload exceeds 9kg, the workflow automatically bypasses standard cartons and selects **Metal Stillages** or **Pallets**.

```text
Pack product 45 (Solid Counterweight Ingot). This part is heavy and will require industrial packaging.
```
- **Expected Outcome:**
  - Auto-resolves: **Solid Counterweight Ingot** (Product 45), Weight: 38.0 kg.
  - Carton filter: Cartons rejected due to weight capacity limit (max 9kg).
  - Winner: `Metal Stillage 1` (`metal_stillages` table, max capacity 1,200 kg).

```text
I need to pack 2 units of an industrial cast iron motor housing measuring 420x280x260mm with weight 18.5kg each.
```
- **Expected Outcome:**
  - Total payload: 37.0 kg.
  - Winner: Heavy-duty `Metal Stillage` or `Metal Pallet`.

```text
Recommend a packaging solution for 4 heavy steel dies, each 300x250x180mm weighing 12kg (total 48kg).
```

---

## 4. Ambiguous Input & Human-In-The-Loop (HITL)

These prompts lack essential physical dimensions or weights, triggering the **Human-in-the-Loop** checkpoint to ask the user for clarification.

```text
I have some metal brackets that need packaging for shipment.
```
- **Expected Outcome:** 
  - Status: `hitl_clarification_required`.
  - Amber notification banner detailing missing dimensions and weight.
  - Quick action suggestion chips displayed in the UI.

```text
Can you find me a box to ship my parts?
```

```text
Please pack 10 items safely into inventory containers.
```

```text
We have new spare parts arriving tomorrow, please recommend packaging.
```

---

## 5. Fragile Parts & Cushioning Rules

These prompts trigger fragility and padding calculations (e.g., glass, lenses, delicate electronic sensors), automatically adding protective clearance.

```text
Pack 2 units of fragile optical lens assemblies measuring 120x80x50mm, 0.45kg each, made of high-fragility optical glass.
```
- **Expected Outcome:**
  - Padding rule: 25mm to 30mm Polyethylene / Anti-static foam clearance.
  - Effective bounding box accounts for protective cushioning on all faces.

```text
Find packaging for 4 delicate quartz inspection plates: 150x150x20mm, 0.3kg each, high fragility.
```

```text
Pack 6 ceramic insulator components (fragile material) measuring 95x60x60mm, weight 0.5kg each.
```

---

## 6. High Quantity Bulk Packing & Orientation Optimization

These prompts test the 3D Extreme Point algorithm under dense packing conditions with 20 to 100+ items.

```text
Pack 48 units of rectangular electronic PCB modules measuring 65x45x25mm with weight 0.08kg each.
```
- **Expected Outcome:**
  - Extreme Point evaluation explores 6 orthogonal orientations.
  - Identifies optimal orientation $(dx, dy, dz)$ for maximum volume efficiency.
  - 3D scene visualizer renders 48 color-coded blocks.

```text
Find the best container to pack 32 aluminum heat sinks: 90x60x35mm, weight 0.15kg each.
```

```text
Calculate 3D packing for 75 small plastic connector clips: 40x25x20mm, weight 0.02kg each.
```

---

## 7. Edge Cases & Boundary Constraints

These prompts test boundary enforcement when parts are too large for standard inventory containers.

```text
Can you pack a large structural steel beam measuring 1400x400x300mm with weight 45kg?
```
- **Expected Outcome:**
  - Evaluates warehouse dimensions; if exceeded, reports unplaced items and recommends custom box fabrication.

```text
Pack 100 units of large machine covers: 500x350x250mm, 3kg each.
```
- **Expected Outcome:**
  - Reports volume overflow; highlights partial placement count or suggests bulk palletizing.

---

## 8. HITL Follow-Up Resolution Prompts

When the assistant pauses for HITL clarification, use these prompts to provide the missing specifications and resume the workflow:

```text
The parts are 140mm in length, 90mm in width, 60mm in height, weighing 1.2kg each, quantity 4.
```

```text
Add specifications: dimensions 180x120x70mm, weight 1.5kg, SNP 6 units.
```

```text
Use product 1 from the catalog with 64 units.
```

