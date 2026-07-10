# Amazon SP-API Production Plugins

## Purpose

Add real Amazon SP-API production support as optional discovery and validation plugins.

Amazon data serves two roles:

1. Discovery: find comparable ASINs and candidate products.
2. Validation: estimate pricing, offers, and FBA fees so the app can calculate the max landed cost.

The terminal should not become an Amazon-only clone of Product Opportunity Explorer. Amazon SP-API is one source in the discovery layer and one input to the validation layer.

## Existing Repo Context

The repo currently has:

- plugin registry under `backend/app/plugins/registry.py`
- `amazon_mock` ingestion plugin
- cost ceiling defaults in `.env.example`
- economics analyzer that uses configurable defaults until live Amazon Product Fees data is available
- FastAPI endpoints for pipeline trigger and product details

Do not rewrite these foundations. Add narrow SP-API plugins.

## New Plugins

Add these ingestion/analyzer plugins:

```text
backend/app/plugins/ingestion/amazon_catalog_spapi/
backend/app/plugins/ingestion/amazon_pricing_spapi/
backend/app/plugins/ingestion/amazon_fees_spapi/
backend/app/plugins/analyzers/amazon_comparable_asins/
```

### 1. `amazon_catalog_spapi`

Purpose:

- Given a keyword/product candidate, find comparable ASINs.
- Store catalog evidence as `RawObservation`.
- Create market signals for catalog metadata where possible.
- Feed both discovery and validation.

Input:

```json
{
  "query": "facial ice roller",
  "category": "beauty",
  "limit": 10
}
```

Output:

- RawObservation with `entity_type="marketplace_listing"`
- metadata including:
  - ASIN
  - title
  - brand if available
  - category/product type
  - dimensions if available
  - image URL if available
  - sales rank if available
  - source URL if available

### 2. `amazon_pricing_spapi`

Purpose:

- Given a list of comparable ASINs, retrieve pricing/offer data.
- Store market price signals.
- Support modeled sale price selection.

Output MarketSignals:

```text
price
offer_count
featured_offer_price
competitive_price
lowest_offer_price
```

Do not fail the entire pipeline if pricing is unavailable for an ASIN.

### 3. `amazon_fees_spapi`

Purpose:

- Given ASIN + modeled price, call Product Fees API and persist an FBA cost model.
- This is the key plugin for the max-landed-cost workflow.

Output CostModel:

```text
model_name = "amazon_fba_fee_estimate"
selling_price
referral_fee_per_unit
fulfillment_fee_per_unit
total_amazon_fees
fee_estimate_source = "amazon_spapi_product_fees"
comparable_asin
```

If Amazon returns multiple fee components, preserve the raw components in JSON metadata.

### 4. `amazon_comparable_asins` analyzer

Purpose:

- Associate Amazon ASIN observations with the canonical ProductCandidate.
- Select a modeled price and modeled fee range from comparable ASINs.
- Create ProductInsight explaining which ASINs are being used as proxies.

## Configuration

Add to `.env.example`:

```env
AMAZON_SP_API_ENABLED=false
AMAZON_SP_API_ENV=sandbox
AMAZON_SP_API_ENDPOINT_SANDBOX=https://sandbox.sellingpartnerapi-na.amazon.com
AMAZON_SP_API_ENDPOINT_PRODUCTION=https://sellingpartnerapi-na.amazon.com
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER
AMAZON_LWA_CLIENT_ID=replace_me
AMAZON_LWA_CLIENT_SECRET=replace_me
AMAZON_LWA_REFRESH_TOKEN=replace_me
AMAZON_REQUEST_TIMEOUT_SECONDS=20
AMAZON_CATALOG_SEARCH_LIMIT=10
AMAZON_FEES_DEFAULT_MODELED_PRICE=24.99
```

## Auth Requirements

Implement:

```text
backend/app/plugins/ingestion/amazon_spapi_client.py
```

Responsibilities:

- read env config
- exchange refresh token for access token
- cache access token until near expiry
- support sandbox/production endpoint switching
- redact secrets from logs
- raise typed errors

Do not expose Amazon credentials to frontend.

## Data Model Additions

If existing JSON metadata is sufficient, do not add tables yet.

If needed, add optional fields to CostModel metadata:

```json
{
  "comparable_asin": "B0...",
  "fee_estimate_id": "...",
  "fee_components": [],
  "amazon_spapi_env": "production",
  "estimate_confidence": "proxy_asin"
}
```

## Important Rule

Product Fees estimates for a new private-label product are proxy estimates based on comparable ASINs. Every UI display must label them as:

```text
Estimated from comparable ASINs, not guaranteed actual fees.
```

## API Behavior

The existing pipeline should support:

```bash
curl -X POST http://localhost:8000/ingestion/run \
  -H 'Content-Type: application/json' \
  -d '{"plugins":["amazon_catalog_spapi"],"query":{"query":"facial ice roller","limit":10}}'
```

Then a follow-up run should be able to run pricing/fees against found ASINs.

Codex may implement either:

1. separate plugin runs, or
2. one combined `amazon_spapi_research` orchestrator plugin that internally calls catalog → pricing → fees.

Prefer separate plugins unless plumbing becomes too awkward.

## UI Requirements

On product detail page show:

- Comparable ASIN table
- Amazon price range
- Selected modeled price
- Fee estimate range
- Chosen fee estimate used in cost ceiling
- Warning that fee estimates are based on comparable ASINs

## Tests

Add tests for:

- missing credentials disables plugin
- sandbox env uses sandbox endpoint
- production env uses production endpoint
- token exchange is mocked in tests
- catalog response maps to RawObservation
- pricing response maps to MarketSignals
- fee response maps to CostModel
- plugin failure results in partial pipeline failure, not crash
- frontend/API never expose credentials

## Acceptance Criteria

- Amazon SP-API plugins can run in sandbox/mock mode without real calls.
- Production mode can be enabled through env vars only.
- Amazon catalog/pricing/fees data flows into product detail.
- Cost ceiling can prefer live Product Fees estimates over default assumptions.
- Existing mock/default flow still works when Amazon plugins are disabled.
