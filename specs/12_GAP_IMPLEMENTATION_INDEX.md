# Gap Implementation Index — Validation-First Product Discovery Terminal

## Purpose

This spec pack updates the Product Discovery Terminal after the initial MVP implementation.

The current repo already has the important foundation:

- local-first FastAPI + Next.js app
- scheduled batch pipeline
- ingestion plugins
- analyzer plugins
- raw observations
- normalization
- scoring
- cost ceiling calculation
- product detail UI
- mock/manual plugins
- disabled external API plugin scaffolding

The next phase should **keep discovery as a core part of the product**, but every discovered candidate should flow through a stronger validation layer before it is treated as a real opportunity.

Amazon already provides Product Opportunity Explorer, so the terminal should not become a shallow clone of Amazon-only niche discovery. The alpha should become:

> A validation-first product discovery terminal.

The system should answer:

> Which products are worth investigating, and what must be true economically, operationally, and supplier-wise for them to be viable?

## Strategic Direction

Do not pivot away from discovery.

Instead, improve discovery by requiring validation.

```text
Discover candidates
→ normalize products
→ find comparable ASINs
→ estimate Amazon pricing and fees
→ calculate max landed cost
→ validate supplier quotes
→ apply custom constraints
→ check cross-source evidence
→ create paper-trading snapshots
→ recommend pursue / investigate / watch / skip
```

## What Discovery Means

Discovery remains responsible for surfacing candidates from sources such as:

- Amazon SP-API catalog search
- manual Product Opportunity Explorer imports
- manual CSV imports
- supplier quote imports
- Reddit/social/trend plugins
- future Keepa or third-party imports
- future supplier directories
- future marketplace APIs

Discovery should produce candidate products. Validation determines whether those candidates are viable.

## What Validation Adds

Validation adds the parts Amazon Product Opportunity Explorer does not know about:

- your target margin
- your max landed cost
- your supplier quotes
- your product constraints
- your risk tolerance
- your fulfillment assumptions
- your source confidence
- your paper-trading history

## New Spec Files

Add these files to the existing `specs/` folder:

```text
12_GAP_IMPLEMENTATION_INDEX.md
13_AMAZON_SP_API_PRODUCTION_PLUGINS.md
14_COST_CEILING_ENGINE_V2.md
15_SUPPLIER_VALIDATION_WORKFLOW.md
16_CUSTOM_CONSTRAINTS_AND_RISK_RULES.md
17_CROSS_SOURCE_VALIDATION.md
18_BACKTESTING_AND_PAPER_TRADING.md
19_FRONTEND_VALIDATION_FIRST_DISCOVERY_UI.md
20_CODEX_IMPLEMENTATION_PLAN_GAPS.md
```

## Implementation Order

1. Amazon SP-API production plugins.
2. Cost Ceiling Engine v2.
3. Supplier validation workflow.
4. Custom constraints and risk rules.
5. Cross-source validation.
6. Backtesting / paper trading.
7. Frontend validation-first discovery UI.
8. Tests and docs.

## Non-Goals

Do not implement:

- content generation
- TikTok/YouTube/Pinterest posting
- paid ads
- FBA listing creation
- order management
- inventory management
- buyer communication
- scraping Seller Central or Product Opportunity Explorer
- automatic supplier messaging
- automatic purchasing

## Core Acceptance Test

A user should be able to enter or discover:

```text
facial ice roller
target margin: 30%
constraints: no battery, no liquid, no fragile glass
supplier quote: $3.20 unit cost + $0.70 freight + $0.40 packaging
```

The app should return:

```text
Discovery source / candidate origin
Comparable ASINs found
Modeled sale price
Estimated Amazon fees
Max landed cost
Supplier landed cost
Margin of safety
Constraint pass/fail
Cross-source evidence summary
Decision: pursue / investigate / watch / skip
```

## Architectural Rules

- Keep discovery plugins source-specific.
- Keep validation/scoring source-agnostic.
- Do not hardcode Amazon assumptions outside Amazon plugins and economics config.
- Keep supplier validation independent from Alibaba.
- Keep Product Opportunity Explorer as manual input only unless Amazon exposes an official API/export.
- Every score or decision must show an explanation and the evidence used.
- A product should not become a strong opportunity from discovery evidence alone; it needs validation evidence.
