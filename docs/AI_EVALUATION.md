# AI generation evaluation

GroundsOps evaluates each successfully returned landscape image before presenting its quality
result as trusted. Generation success and evaluation success are intentionally separate: a
provider can return a valid image that still changes too little inside the requested mask or
changes too much outside it.

## Quality gates

Evaluator `pixel-change-v1` compares the source and output at the pixel level:

- source, output, and mask dimensions must match;
- at least 20% of pixels inside the editable mask must materially change;
- no more than 8% of protected pixels outside the mask may materially change;
- a pixel is materially changed when its mean RGB difference exceeds 5% of the channel range.

The three thresholds are configurable with:

```text
EVALUATION_MASKED_CHANGE_MIN=0.20
EVALUATION_PROTECTED_CHANGE_MAX=0.08
EVALUATION_PIXEL_CHANGE_THRESHOLD=0.05
```

Each result is persisted in `generation_evaluations` with the evaluator version, observed
ratios, thresholds, pass/fail result, failure reasons, and evaluation latency. This makes model
or prompt changes comparable over time instead of relying on anecdotal visual inspection.

## API

Authenticated organization members can retrieve the evaluation for a generation:

```http
GET /api/v1/generations/{generation_job_id}/evaluation
```

The endpoint is organization-scoped and returns `404` both when the job is outside the caller's
tenant and when no evaluation exists yet.

## Validation

Run:

```powershell
ruff check .
pytest
```

The deterministic tests use small in-memory PNGs and do not call an external inference provider.
They cover a passing masked edit, protected-region damage, dimension mismatch, and an empty mask.

## Next evaluation iterations

Pixel-level gates are a reproducible baseline, not a complete measure of design quality. Future
versions should add a labeled review set, material/prompt cohorts, perceptual similarity, human
acceptance outcomes, and regression dashboards. Version every evaluator so historical results
remain interpretable when metrics or thresholds change.
