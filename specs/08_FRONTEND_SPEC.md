# Frontend Spec

## Frontend Goal

Build a terminal-style UI for browsing, filtering, and understanding product opportunities.

The UI should feel more like an intelligence workspace than a generic admin dashboard.

## Stack

- Next.js
- TypeScript
- TailwindCSS
- shadcn/ui
- TanStack Query
- Recharts or lightweight charting library

## Pages

### 1. Dashboard

Route:

```text
/
```

Purpose:

Show top opportunities and recent pipeline health.

Sections:

- Top opportunities
- Score distribution
- Recently updated products
- Plugin run status
- Run pipeline button

Top opportunity card should show:

- product name
- category
- final score
- recommendation
- demand score
- margin score
- risk score
- short thesis

### 2. Product Search

Route:

```text
/products
```

Features:

- search box
- category filter
- score filter
- recommendation filter
- sortable table

Columns:

- product
- category
- final score
- demand
- growth
- margin
- risk
- recommendation
- updated date

### 3. Product Detail

Route:

```text
/products/[id]
```

Sections:

1. Header
   - canonical name
   - category
   - latest score
   - recommendation

2. Opportunity thesis
   - explanation from scoring engine

3. Score breakdown
   - demand
   - growth
   - competition
   - margin
   - pain point
   - risk
   - confidence

4. Signals
   - market signals
   - supplier signals
   - cost models

5. Insights
   - review summaries
   - complaint clusters
   - risk flags
   - differentiation ideas

6. Evidence
   - recent raw observations
   - source links if available

### 4. Plugin Status

Route:

```text
/plugins
```

Display:

- installed ingestion plugins
- installed analyzer plugins
- enabled/disabled state
- latest run status
- records created
- error messages

### 5. Pipeline Runs

Route:

```text
/runs
```

Display:

- recent runs
- plugin name
- status
- started time
- duration
- records created
- errors

## UI Principles

- Keep the interface dense but readable.
- Prioritize scores and explanations.
- Every recommendation must show why.
- Make evidence easy to inspect.
- Avoid ecommerce-store aesthetics.
- Avoid over-polished marketing UI.

## Components

Recommended components:

```text
OpportunityCard
ScoreBadge
ScoreBreakdown
ProductTable
SignalTable
InsightPanel
PluginRunTable
RunPipelineButton
RecommendationBadge
EvidenceList
```

## API Client

Use TanStack Query.

Suggested hooks:

```typescript
useProducts(filters)
useProduct(id)
useOpportunities(filters)
usePlugins()
usePluginRuns()
useRunPipeline()
```

## MVP Visual Design

Dark terminal-inspired UI is acceptable.

Suggested layout:

- left sidebar
- main content area
- dense tables
- score badges
- expandable evidence rows

## Empty States

Handle:

- no products yet
- no plugin runs yet
- no scores yet
- failed plugin run
- backend unavailable

## Run Pipeline Button

Dashboard should include a button:

```text
Run Pipeline
```

On click:

- call `POST /ingestion/run`
- show loading state
- show success/failure summary
- refresh dashboard data

## Acceptance Criteria

Frontend is complete when:

- user can run pipeline from UI
- user can view ranked opportunities
- user can search/filter products
- user can open product detail
- user can inspect score explanations
- user can view plugin run failures
