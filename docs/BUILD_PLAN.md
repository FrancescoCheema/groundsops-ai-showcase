# GroundsOps AI detailed build plan

This plan is organized as vertical slices. Every slice must have a migration, tenant-scoped API, tests, observable status, documentation, and a working demonstration before the next begins.

## Slice 1: management backbone — implemented

### Delivered

- organization users with admin, manager, designer, and crew roles
- customers and customer-owned properties
- material categories and variants
- design projects
- preliminary quotes with currency and assumptions
- organization-scoped database queries
- cross-organization reference rejection
- migration `0002`

### Definition of done

- linting passes
- eight automated tests pass
- upgrade → downgrade → upgrade succeeds
- customer → property → design → quote works through the API

## Slice 2: authentication and authorization — implemented

### Delivered

- signed HS256 development tokens with issuer, audience, issue, and expiry claims
- development-only organization/administrator bootstrap
- Swagger Bearer authentication
- organization and role derived from token rather than request headers
- active database-user and stale-role validation on every request
- admin-only user creation
- manager/admin customer, property, quote, and work-order changes
- designer/manager/admin material and design changes
- read access for authenticated organization users
- production RS256/JWKS validation path for Cognito/OIDC
- missing, invalid, expired, role-denied, and organization-spoofing tests

### Ticket 2.1: identity adapter

1. Define an `AuthenticatedPrincipal` containing subject, email, organization, and roles.
2. Create a local development identity provider for tests and local demos.
3. Create a Cognito JWT verifier adapter without coupling route logic to Cognito.
4. Replace trusted `X-Organization-ID` input with organization claims from the authenticated principal.
5. Preserve a clearly marked development-only mode.

Status: complete.

### Ticket 2.2: policy enforcement

1. Define permissions for admin, manager, designer, crew, and customer.
2. Add route-level policy dependencies.
3. Require manager/admin for quote status changes.
4. Require designer/manager/admin for visual render requests.
5. Require customer ownership or staff permission to view a property.

Status: staff policies complete; customer identity/ownership remains part of the customer portal.

### Tests

- missing/invalid token is rejected
- expired token is rejected
- user cannot select another organization by changing a header
- crew cannot approve quotes
- customer cannot view another customer's property
- disabled organization user is rejected

Implemented security suite: fourteen total automated tests pass.

## Local authenticated Swagger workflow

1. Start PostgreSQL and the API.
2. Call `POST /api/v1/auth/development-token` with an existing organization ID and active user email.
3. Copy `access_token` without quotation marks.
4. Select **Authorize** in Swagger.
5. Paste the token value; Swagger sends it as a Bearer token.
6. Call management endpoints without an organization header.
7. Confirm a crew token receives `403` on customer creation.
8. Confirm an invalid or expired token receives `401`.

Never enable the development token endpoint in production.

## Slice 3: object storage and site capture

### Ticket 3.1: data model and migration

Add:

- `SiteCapture`
- `CaptureStatus`: pending, uploaded, validating, ready, rejected, failed
- original object key
- sanitized object key
- MIME type, size, checksum, width, height, captured time
- optional coarse location stored separately from exact EXIF
- quality scores and rejection reasons

### Ticket 3.2: storage interface

Define a vendor-neutral interface:

```python
class ObjectStorage:
    def create_upload(self, object_key, content_type, max_bytes): ...
    def object_exists(self, object_key): ...
    def create_download(self, object_key, expires_in): ...
    def delete(self, object_key): ...
```

Implement:

- filesystem/MinIO adapter locally
- S3 adapter later
- private objects only
- short-lived authorized URLs

### Ticket 3.3: capture validation

1. Accept JPEG, PNG, and HEIC when decoding support is confirmed.
2. Reject unsupported MIME signatures rather than trusting extensions.
3. Enforce size and pixel limits.
4. Decode the image safely.
5. remove EXIF and exact GPS data
6. generate a sanitized derivative
7. calculate blur, brightness, and resolution indicators
8. mark capture ready or rejected with reasons

### Tests

- executable renamed `.jpg` is rejected
- oversized image is rejected
- duplicate completion is idempotent
- EXIF/GPS is removed
- other organization cannot complete or access capture
- missing object produces controlled failure

## Slice 4: design project and manual mask editor

### Backend

1. Add `SurfaceMask` and `DesignVersion` entities.
2. Preserve original mask and every corrected version.
3. Store masks as lossless grayscale PNGs.
4. Require mask dimensions to match the sanitized source image.
5. Validate that mask coverage is plausible.
6. Create immutable design versions.

### Frontend

1. Create a responsive Next.js application.
2. Build customer/property/design navigation.
3. Use phone camera capture with file-upload fallback.
4. Display the sanitized image on a canvas.
5. Implement brush, erase, undo, redo, zoom, and reset.
6. Show mask overlay opacity control.
7. Require explicit confirmation of the editable region.

### Tests

- mask dimensions must match source
- zero-area and full-image masks require warnings/rejection
- mask is scoped to design and organization
- correction history is immutable
- browser test completes capture → mask confirmation

## Slice 5: baseline surface segmentation

### Implementation

1. Define a `SegmentationProvider` interface.
2. Create an evaluation set containing lawn, soil, pavement, gravel, mulch, and unsupported scenes.
3. Establish a manual-mask baseline before selecting a model.
4. Evaluate candidate segmentation models for supported surfaces.
5. Store model name, version, latency, and raw confidence.
6. Generate a proposed mask asynchronously.
7. Require user confirmation/correction before rendering.

### Metrics

- intersection-over-union against reference masks
- precision/recall by material/surface category
- percentage of masks requiring correction
- correction time
- segmentation latency and cost

### Gate

Do not claim automatic surface detection until results are reported by scene category. Unsupported scenes must fall back to manual masking.

## Slice 6: material visual catalog

### Data additions

- material reference images/textures
- supplier-independent material attributes
- colour and pattern
- dimensions and package unit
- recommended installation depth
- default waste factor
- permitted surface categories
- visualization prompt fragment

### Workflow

1. Organization administrator creates or imports a material.
2. Reference media is validated and stored privately/publicly as appropriate.
3. Designer reviews the visual representation.
4. Customer sees controlled variants rather than arbitrary prompts.
5. Design records the exact selected material version.

## Slice 7: asynchronous AI rendering

### Data model

Add:

- `RenderJob`
- queued, running, completed, failed, cancelled states
- provider/model/version
- input design version and material variant
- prompt/template version
- input/output object keys
- latency, retry count, token/compute units, and estimated cost
- failure category

### Processing

1. API validates design, capture, mask, and material ownership.
2. API creates one render job and enqueues its ID.
3. Worker obtains source, approved mask, and material references.
4. Worker invokes an image-edit provider through a vendor-neutral interface.
5. Worker validates output dimensions and decodability.
6. Worker runs protected-region comparison.
7. Unsafe or corrupt output is rejected.
8. Worker stores output and completes the job.
9. Client polls or receives an event and displays the result.

### Reliability

- idempotency key prevents accidental duplicate charges
- bounded retries only for transient errors
- dead-letter queue for exhausted jobs
- per-user and per-organization generation limits
- timeout and cancellation support
- model/provider fallback only after separate evaluation

## Slice 8: visual evaluation

### Dataset

Build consented or synthetic cases across:

- bright/dark scenes
- dry/wet surfaces
- winter/summer vegetation
- obstructions
- steep camera angles
- mixed surfaces
- protected people, plants, buildings, fences, and vehicles

### Automated metrics

- mask IoU
- changed pixels outside approved mask
- structural similarity outside mask
- output image validity
- latency and cost

### Human rubric

- selected material recognizable
- perspective believable
- lighting/shadows acceptable
- boundary quality acceptable
- protected objects preserved
- design useful for a customer decision

Commit evaluation reports and block deployment on critical regressions.

## Slice 9: measurements and deterministic estimation

### Measurement sources

- manually supplied length/width
- one known reference dimension
- supported LiDAR/depth measurement
- guided multi-view reconstruction
- on-site professional measurement

Every measurement stores source, unit, uncertainty, time, and verifier.

### Estimate calculation

1. Normalize dimensions to SI units internally.
2. Calculate surface area.
3. Apply installation depth where applicable.
4. Apply compaction and waste factor.
5. Convert volume/area to provider package units.
6. Round packages upward where necessary.
7. Record every intermediate value.
8. Display exclusions for labour, delivery, tax, removal, and site preparation.

### Tests

- metric and imperial conversions
- decimal rounding
- zero/negative dimensions rejected
- package count rounds safely
- price calculation deterministic
- estimate remains linked to exact design/material versions

## Slice 10: nearby providers

### Initial demonstration

Use a synthetic catalog with provider branches around Metro Vancouver.

### Data model

- provider
- branch and coordinates
- service radius
- provider product/SKU
- package size and unit
- price and currency
- availability status
- source and freshness timestamp

### Search sequence

1. Ask for location permission or postal code.
2. Geocode coarse location.
3. Find branches within a configurable radius.
4. Filter products compatible with selected material.
5. Convert required quantity to packages.
6. Rank by total material cost, distance, and freshness.
7. Show assumptions rather than claiming guaranteed inventory.

Real provider data is introduced only through an official API, feed, catalog upload, or authorized agreement.

## Slice 11: quote and work-order conversion

1. Customer selects a design.
2. System creates a preliminary estimate.
3. Manager verifies measurements, material, labour, exclusions, and provider data.
4. Manager converts estimate to a formal quote.
5. Customer accepts/rejects the quote.
6. Authorized manager creates a work order.
7. Every transition creates an audit event.
8. AI never performs the approval transition.

## Slice 12: document assistant

1. Upload contracts and property documents.
2. Extract text with page and section metadata.
3. Store embeddings in PostgreSQL/pgvector.
4. Retrieve only within organization and property boundaries.
5. Answer with page-level citations.
6. Propose work tasks from evidence.
7. Evaluate retrieval separately from generation.
8. Require approval for all operational changes.

## Slice 13: AWS and delivery platform

- Terraform modules
- ECS Fargate API/web/worker services
- RDS PostgreSQL with pgvector
- private S3 source/render buckets
- SQS queues and dead-letter queues
- Cognito identity
- Secrets Manager
- ECR
- CloudFront where authorized media delivery requires it
- GitHub Actions with OIDC
- vulnerability, secret, dependency, container, and IaC scanning
- deployment smoke tests and AI evaluation gates

## Slice 14: observability and cost control

- HTTP and database metrics
- queue depth and job age
- segmentation/render latency and failures
- generation cost by model, organization, and material
- mask correction and design acceptance rates
- estimate error by measurement method
- provider-catalog freshness
- distributed traces across API → queue → worker → model → storage
- budgets, quotas, alerts, runbooks, and rollback

## Slice 15: consented improvement system

1. Record consent version and permitted uses.
2. Support refusal and revocation.
3. Create de-identification workflow.
4. Isolate approved data from operational data.
5. Quality-review corrected masks and feedback.
6. Version datasets.
7. Register candidate prompt/model changes.
8. Evaluate offline.
9. Canary release successful candidates.
10. Monitor and roll back regressions.

## Slice 16: guided multi-view and optional AR

### Multi-view first

- capture guidance
- view-quality checks
- known measurement or depth input
- cross-view geometry
- confidence interval
- consistent design across views

### AR experiment

- validate customer demand
- build iOS ARKit/RealityKit proof of concept
- plane detection and anchoring
- physical scale and perspective
- occlusion
- device compatibility and frame rate
- retain still-image fallback
- consider Android ARCore only after iOS results justify it

## Global engineering rules

- No organization-owned query without an organization boundary.
- No state-changing AI action without deterministic validation and authorization.
- No customer image used for improvement without explicit consent.
- No estimate presented without assumptions, source, unit, and confidence.
- No provider price presented without source and freshness.
- No model upgrade without a versioned evaluation comparison.
- No asynchronous operation without idempotency, status, bounded retries, and observable failure.
- No milestone is complete unless the developer can explain and modify it without AI assistance.
