# Amazon Data Handling

Data owner: Adam Menker

## Amazon Data Accessed

Product Discovery Terminal is scoped to access only data needed for internal product research and FBA unit-economics analysis:

- Catalog data.
- Comparable ASIN metadata.
- Pricing and offer information.
- Product fee estimates.

## Amazon Data Not Accessed

The application is designed not to access:

- Buyer PII.
- Buyer messages.
- Order or customer details.
- Shipping addresses.
- Tax data.
- Restricted role data.
- Buyer communication workflows.

## Data Usage

Amazon Information is used only for:

- Internal product opportunity research.
- Comparable ASIN research.
- FBA fee modeling.
- Margin analysis.
- Max landed-cost calculation for supplier research.

## Data Retention

- Retain only data needed for product research.
- Avoid storing data categories outside the approved scope.
- Local development databases may be deleted/reset when no longer needed.
- If production storage is introduced, retention rules must be documented before production use.

## Data Sharing

- Amazon Information is not shared with third parties.
- Amazon Information is not made public.
- Amazon Information is not sold or used for third-party seller services.
- The application is not offered as a public SaaS product.

