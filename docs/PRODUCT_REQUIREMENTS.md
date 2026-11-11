# Product requirements

## Product vision

GroundsOps AI is a landscaping management system with AI assistance and visual design support. It connects the full customer journey:

1. capture and manage a customer/property
2. understand documents and existing site requirements
3. photograph or scan an outdoor space
4. select the surface or area to change
5. visualize proposed materials such as grass, pavers, gravel, or mulch
6. estimate area and material quantity with clearly stated confidence
7. find matching products from nearby participating providers
8. produce a transparent preliminary estimate
9. convert the accepted design into a human-approved quote and work order

The generated visualization is a design aid, not a guaranteed construction outcome. The interface must display that limitation.

## Problem statement

Landscaping teams receive obligations and property details through contracts, maintenance specifications, inspection notes, and customer requests. Finding the correct requirement and translating it into a work order is slow and can result in missed work. GroundsOps AI will retrieve the relevant evidence, answer operational questions with citations, and propose structured work orders that require human approval.

## Primary user

A landscaping operations manager responsible for reviewing property requirements and creating work orders.

## Additional users

- Customer: captures a space, explores design options, and requests an estimate.
- Landscape designer/estimator: corrects masks and dimensions, selects materials, and reviews quantities.
- Crew member: views approved work orders and design references.
- Provider administrator: maintains available products, coverage area, price, unit, and stock freshness.
- Organization administrator: manages users, permissions, catalogs, and audit records.

## Product modules

### Customer and property management

- customers, contacts, properties, and service locations
- photos, measurements, documents, notes, and design history
- quotes, approvals, work orders, and status tracking

### AI operations assistant

- cited document questions
- property-specific requirements
- structured work-order proposals
- human approval and audit history

### AI design visualizer

- phone-camera capture or photo upload
- image-quality and supported-scene checks
- user-selected editable region
- automatic surface segmentation with manual correction
- material and style selection
- generated before/after variants that preserve buildings and non-selected areas
- design version history and customer feedback

### Material and estimate assistant

- optional location permission or manually supplied postal code
- provider and product catalog
- material-to-product matching
- distance and service-area filtering
- estimated surface area, depth, waste factor, quantity, unit, and price
- source, timestamp, tax/delivery exclusions, and confidence indicators
- human-reviewed quote conversion

## Visualizer levels

### Level 1: captured-photo visualization

The customer captures a still image, marks the area to change, chooses a material, and receives a generated rendering. This is the first credible release.

### Level 2: guided multi-view capture

The customer captures several angles plus one known measurement. The system produces more consistent designs and a better area estimate.

### Level 3: live-camera AR preview

The mobile client detects and tracks surfaces while the camera moves, anchors a material texture to the ground plane, preserves scale and perspective, and updates the preview in real time. This requires a native or AR-capable mobile client using technologies such as ARKit/RealityKit on iOS and ARCore on Android. It is not equivalent to sending individual video frames to an image-generation model.

## Visual generation workflow

1. Request camera and optional location permission with a clear explanation.
2. Capture the original image and immutable metadata.
3. Reject or warn about images that are too dark, blurry, obstructed, or unsupported.
4. Create an initial ground/surface mask.
5. Let the user paint, erase, or confirm the editable region.
6. Select a material from a controlled catalog, not a free-form construction promise.
7. Generate one or more previews using the original image, mask, and material reference.
8. Verify that protected regions have not changed materially.
9. Display the original and generated result together.
10. Save the prompt/model/version, mask, source image, output, latency, and consent record.
11. Let the user accept, reject, or correct the design.

## Learning from user data

The application must not silently train itself on customer images. Improvement follows a governed feedback loop:

1. obtain explicit, revocable consent for product-improvement use
2. separate operational storage from an approved training/evaluation dataset
3. remove precise location, EXIF data, faces, license plates, and other personal information where possible
4. retain the original mask, corrected mask, material choice, generated result, and explicit feedback
5. version and quality-review labels before they enter a dataset
6. evaluate a candidate segmentation, ranking, or generation change offline
7. approve and register the new model/version
8. use a controlled canary or A/B rollout
9. monitor failures and allow rollback

Early improvements should come primarily from better prompts, masks, material reference images, ranking, and evaluation data. Custom model training is a later decision made only when enough consented, high-quality data exists.

## Material provider integration

Provider results must come from an authorized source:

- direct provider API
- provider-managed catalog upload
- commercial product-data agreement
- manually maintained demonstration catalog

The system must not assume that search results equal current inventory. Each offer records provider, branch, location, product/SKU, coverage, price, unit, stock status if available, source, and last-updated timestamp.

The first release uses a synthetic provider catalog. Real providers are integrated only after their API/data terms are confirmed.

## Estimation rules

Every estimate must show its calculation, for example:

```text
estimated area × installation depth × compaction/waste factor
→ required volume
→ provider package conversion
→ material subtotal
```

Photo-only area estimates are low confidence unless a known measurement, depth sensor, LiDAR, multi-view reconstruction, or manual dimension is supplied. A final construction quote requires human verification.

## Initial workflow

1. Create an organization and property.
2. Upload a property contract or maintenance document.
3. Process and index the document.
4. Ask a question scoped to that property.
5. Receive an answer with page-level citations.
6. Generate a draft work order from cited evidence.
7. Review, edit, approve, or reject the proposal.
8. Preserve the decision and supporting evidence in an audit trail.

## Questions to answer with a real landscaping user

Do not invent these answers. Record them after a short interview.

1. What documents are used to decide what work must be completed?
2. Which questions take the most time to answer?
3. How are work orders created today?
4. What errors or omissions occur most often?
5. Who is allowed to approve work?
6. Which information is confidential?
7. Are documents organized by customer, property, contract, or another unit?
8. Are photographs part of the decision process?
9. What fields must every work order contain?
10. What measurable outcome would make this tool useful?
11. Which materials are most frequently quoted: grass, pavers, gravel, mulch, soil, or plants?
12. How is area measured today?
13. What waste factor is normally added for each material?
14. Which local providers are normally used and why?
15. Do customers struggle to imagine the finished design?
16. Would customers accept a still-image visualization, or is live AR genuinely necessary?
17. Which parts of an image must never be changed by the visualizer?
18. What must be verified on-site before a price becomes a formal quote?

## Starter discovery worksheet

Fill in at least 15 real questions in this format:

| User question | Source document | Expected answer | Expected page/section | Consequence if wrong |
|---|---|---|---|---|
| Example: Is weekly mowing included at Cedar Court? | Synthetic maintenance contract | Yes, April through October | Section 3.1 | Incorrect scheduling |

## Initial quality targets

- Retrieval recall@5: at least 85%
- Citation correctness: at least 90%
- Grounded answer rate: at least 85%
- Unsupported claim rate: below 10%
- Median answer latency: below five seconds
- Work-order state changes: always require an authorized human
- Cross-organization retrieval: zero tolerated cases
- Selected-area intersection-over-union for supported surfaces: establish a measured baseline, then target at least 85%
- Protected-region preservation: at least 95% similarity outside the approved mask
- Material identity: selected material remains recognizable in at least 90% of accepted test cases
- Estimate calculation correctness: 100% for deterministic unit conversions
- Provider offer freshness: visible on every result
- Visual generation consent and provenance: recorded for every saved design

## Out of scope for the first AI release

- autonomous dispatching
- payments and invoicing
- real-time AR surface tracking
- automatic construction-grade measurements from a single photograph
- autonomous pricing or binding quotations
- silent training on customer images
- unverified provider inventory
- voice interface
- weather integrations
- complex multi-agent orchestration
- model training
