# Delivery roadmap

Each milestone must be runnable, tested, and explainable before the next begins.

## v0.1 — Application foundation (current)

- FastAPI and PostgreSQL
- organization, property, and work-order models
- explicit organization scoping
- migrations and automated tests
- local container workflow

## v0.2 — Document ingestion

- document metadata and lifecycle states
- local object-storage adapter, followed by S3
- PDF/DOCX/TXT extraction
- asynchronous processing contract
- checksum-based idempotency
- page and section metadata preservation

## v0.3 — Management-system core

- customers, contacts, properties, and organization roles
- photo/design metadata and object-storage abstraction
- material catalog, units, and deterministic estimate records
- quote and approval state machine
- audit history

## v0.4 — Baseline cited retrieval

- pgvector
- chunking and embedding pipeline
- property-scoped vector search
- structured answers with page-level citations
- insufficient-evidence response

## v0.5 — Text evaluation harness

- at least 50 versioned evaluation cases
- retrieval recall and ranking metrics
- groundedness and citation checks
- latency and cost reporting
- committed baseline report

## v0.6 — Retrieval improvement

- metadata filters
- hybrid keyword/vector search
- reranking experiment
- architecture decision based on measured results

## v0.7 — Controlled work-order workflow

- typed tool calls
- draft-only AI writes
- manager approval/rejection
- audit history and feedback
- authorization and replay tests

## v0.8 — Captured-photo visualizer foundation

- mobile-friendly camera capture and upload
- image validation and EXIF/location stripping
- immutable originals and versioned derivatives
- automatic surface mask with paint/erase correction
- controlled grass, paver, gravel, and mulch catalog
- masked image-generation job and status lifecycle
- original/generated comparison and design history
- consent, provenance, latency, and cost records

## v0.9 — Visual quality evaluation

- consented/synthetic scene evaluation set
- segmentation IoU and manual-correction effort
- protected-region preservation checks
- material recognizability and perspective review
- human acceptance/rejection rubric
- visual regression report and deployment gate

## v0.10 — Location-aware materials and estimates

- postal-code/geolocation search with explicit permission
- synthetic provider branches and catalogs
- material-to-product mapping and distance filtering
- deterministic unit and waste-factor calculator
- calculation explanation, freshness, exclusions, and confidence
- human conversion from preliminary estimate to quote

## v0.11 — Security, privacy, and observability

- prompt-injection test suite
- tenant-isolation tests
- request and AI traces
- token, cost, latency, retrieval, and quality metrics
- operational runbooks

Additional visual controls:

- signed object access and tenant isolation
- image malware/content validation
- consent and retention enforcement
- face/license-plate and location privacy controls
- visual job traces and model/prompt provenance
- generation cost, failure, acceptance, and correction metrics

## v0.12 — AWS deployment

- ECS Fargate, RDS PostgreSQL, S3, SQS, Cognito, and Bedrock
- Terraform modules and remote state
- GitHub Actions using AWS OIDC
- image, dependency, secret, and IaC scanning
- deployment smoke tests and evaluation gate

Additional visual infrastructure:

- asynchronous image-generation queue and worker
- private source/render buckets and lifecycle policies
- GPU or managed-model adapter selected through measured cost/quality testing
- content delivery using short-lived authorized URLs

## v0.13 — Governed feedback and improvement loop

- explicit product-improvement consent
- de-identification pipeline
- approved dataset registry and dataset versions
- corrected masks and explicit feedback labels
- offline candidate evaluation
- model/prompt registry, canary rollout, and rollback

## v0.14 — Guided multi-view measurement

- multiple guided camera angles
- reference measurement or supported device depth data
- reconstructed surface geometry and confidence interval
- design consistency across views
- estimator verification workflow

## v0.15 — Optional real-time AR prototype

- validate customer demand before starting
- iOS ARKit/RealityKit proof of concept first
- ground-plane detection, anchoring, scale, occlusion, and material textures
- device compatibility and frame-rate measurement
- Android ARCore follow-up if the experiment is successful
- retain still-image rendering as a fallback

## v1.0 — Validated portfolio release

- testing with real landscaping users
- measurable workflow results
- threat model and architecture diagrams
- cost breakdown and known limitations
- three-minute demo and interview-ready case study

The portfolio v1.0 does not require production-ready live AR. A strong release consists of the management platform, cited assistant, evaluated still-image visualizer, transparent material estimate, real-user validation, security, and cloud delivery. AR remains an evidence-driven extension.

