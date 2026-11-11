# AI quality dashboard

The AI Quality workspace turns persisted generation evaluations into operational metrics for
organization administrators and managers. It answers whether generations are improving, why
they fail, how much they cost, and which outputs need human attention.

## Access control

`GET /api/v1/generation-metrics` requires the `admin` or `manager` role. Every query is scoped to
the authenticated principal's organization. Crew and designer accounts receive `403`, while
another organization's generation records never contribute to the response.

## Metrics

The response includes:

- total, completed, evaluated, passed, failed, and unevaluated generation counts;
- overall evaluation pass rate;
- average generation and evaluation latency;
- recorded estimated provider cost;
- failure-reason counts;
- model-version totals, pass rates, latency, and cost;
- up to 30 active days of quality trends;
- the 20 most recent failed evaluations requiring review.

The endpoint aggregates existing `generation_jobs` and `generation_evaluations`; it introduces
no new database schema or migration.

## Frontend

Administrators and managers see an **AI quality** navigation item. The responsive dashboard uses
native CSS charts so it adds no charting dependency. Selecting a failed review item opens its
design project in Design Studio.

## Validation

```powershell
ruff check .
pytest
cd frontend
npm run build
```

Backend tests cover metric aggregation, management-role enforcement, and tenant isolation.
