# Product Validation Pipeline

Spec 22 is implemented as an extension of the existing validation domain.

## Delivered

- Explicit validation project lifecycle with legal transitions, duplicate prevention, and audit history.
- Immutable marketplace packets tied to recommendation snapshots and canonical effective comparables.
- Manual Product Opportunity Explorer evidence with explicit percent units and observation dates.
- Versioned, editable RFQs with placeholders, Markdown/text copy and download support.
- Reusable supplier records, project quotes, arbitrary quantity tiers, and manual-estimate warnings.
- Decimal landed-cost, contribution-margin, and cost-ceiling calculations with source provenance.
- Marketplace, sourcing, economics, risk, and decision-readiness gates with reasoned overrides.
- `/validations` queue and `/validations/{id}` workspace, plus discovery and product entry points.

## Intentional boundaries

Supplier discovery and outreach remain manual. The system does not scrape reviews, contact suppliers, create purchase orders, change scoring weights, or make final approval decisions. Sample approval is a recorded validation outcome, not an inventory commitment.

The older `/validator` workflow and product-level supplier quote endpoints remain available for backwards compatibility. New validation projects use the richer project-level workflow.
