# Product Discovery Terminal Specs

This folder contains the implementation specification for the **Product Discovery Terminal**, a personal side-project MVP for discovering viable consumer product opportunities.

## Core Product

Build a Bloomberg-like terminal for consumer products.

The system should ingest product, market, trend, review, supplier, and cost signals from pluggable sources, normalize them into product candidates, score opportunities, and present explainable recommendations in a terminal UI.

## Key Architectural Decision

The MVP is **not event-driven**.

Use a low-cost scheduled batch pipeline:

```text
scheduled job
→ ingestion plugins
→ raw observations
→ normalization
→ analyzer plugins
→ scoring
→ terminal dashboard
```

The design should remain **event-compatible** so it can later migrate to queues/workers if scale requires it, but do not introduce Kafka, SQS, Celery clusters, Lambda fan-out, or complex AWS infrastructure for the MVP.

## Documents

Read these in order:

1. `01_VISION.md`
2. `02_ARCHITECTURE.md`
3. `03_DATA_MODEL.md`
4. `04_PLUGIN_SDK.md`
5. `05_PIPELINE_ORCHESTRATION.md`
6. `06_SCORING_ENGINE.md`
7. `07_BACKEND_SPEC.md`
8. `08_FRONTEND_SPEC.md`
9. `09_IMPLEMENTATION_PLAN.md`
10. `10_TESTING_AND_QUALITY.md`
11. `11_CODEX_INSTRUCTIONS.md`

## MVP Success Criteria

The MVP is complete when:

- The app runs locally with Docker Compose.
- Mock/manual ingestion plugins can load product observations.
- Observations normalize into canonical product candidates.
- Analyzer plugins generate product insights.
- The scoring engine ranks product opportunities.
- The UI shows a searchable opportunity dashboard.
- Product detail pages show evidence, costs, risks, and an opportunity thesis.
- A new ingestion plugin can be added without modifying core pipeline logic.
