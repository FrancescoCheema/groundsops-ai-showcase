# Visual landscaping system plan

## Core entities to add

| Entity | Purpose |
|---|---|
| Customer | Customer identity scoped to an organization |
| SiteCapture | Original photo/video/depth metadata and capture quality |
| DesignProject | Property design goal, status, and owner |
| DesignVersion | Immutable combination of source, selection, settings, and result |
| SurfaceMask | Automatic and user-corrected editable region |
| Material | Canonical grass, paver, gravel, mulch, soil, or plant option |
| MaterialVariant | Texture, colour, dimensions, installation depth, and reference media |
| RenderJob | Asynchronous visual-generation request and lifecycle |
| Measurement | Source, value, unit, uncertainty, and verifier |
| Provider | Supplier organization and integration source |
| ProviderBranch | Location, service area, and contact metadata |
| ProviderProduct | SKU, material mapping, price unit, availability, and freshness |
| Estimate | Area, quantity, waste, delivery/tax exclusions, and confidence |
| ConsentRecord | Allowed data use, version, time, and revocation status |
| DesignFeedback | Accept/reject, reason, corrected mask, and chosen variant |

## Service boundaries

- Capture service: upload, validation, metadata stripping, and storage.
- Segmentation service: creates a candidate surface mask.
- Render service: edits only the approved region using material references.
- Measurement service: combines manual, depth, or multi-view measurements.
- Catalog service: manages materials, providers, products, and freshness.
- Estimate service: deterministic quantity and price calculations.
- Feedback service: records explicit user judgments and consent.
- Evaluation service: compares candidate versions against fixed datasets.

## Minimum still-image API sequence

1. `POST /properties/{id}/design-projects`
2. `POST /design-projects/{id}/captures/presign`
3. `POST /captures/{id}/complete`
4. `POST /captures/{id}/segment`
5. `PUT /surface-masks/{id}` after user correction
6. `GET /materials`
7. `POST /design-projects/{id}/render-jobs`
8. `GET /render-jobs/{id}` until completion
9. `POST /design-versions/{id}/feedback`
10. `POST /design-versions/{id}/estimates`
11. `GET /estimates/{id}/provider-options`

## Evaluation datasets

Maintain separate, versioned datasets for:

- lawn, soil, paver, gravel, mulch, and mixed/unsupported surfaces
- different seasons, lighting, weather, camera angles, and obstructions
- protected objects such as buildings, fences, people, plants, and vehicles
- correct surface masks and corrected user masks
- material reference/recognition pairs
- measurement examples with known ground truth
- provider matching and deterministic unit-conversion cases

## Portfolio evidence

The finished case study should report:

- segmentation quality before and after user correction
- percentage of protected pixels changed outside the mask
- visual acceptance rate by material and scene category
- generation latency and cost
- estimate error by measurement method
- provider-catalog freshness and match accuracy
- consented feedback volume and model/prompt version comparison
- one documented failure, root cause, mitigation, and regression test

