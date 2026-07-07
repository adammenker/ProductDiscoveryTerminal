# Vision

## Mission

Build a **Bloomberg Terminal for consumer product opportunities**.

The system helps a solo entrepreneur answer:

> What products are worth selling next?

It should identify products with:

- rising demand
- weak or fragmented competition
- recurring customer pain points
- viable manufacturing or sourcing economics
- acceptable operational risk
- sufficient margin after fulfillment costs

## Product Thesis

Most ecommerce sellers fail because they commit capital before they understand demand, competition, and unit economics.

This system exists to reduce that risk.

It should not start by asking:

> How do I generate TikToks?

or:

> How do I launch an Amazon FBA listing?

It should start by asking:

> Is this product opportunity real?

## Core User

Initial user:

- solo technical founder
- building a personal side project
- wants high automation
- does not want to manually browse product catalogs for hours
- does not want to touch physical inventory
- wants the system to eventually support FBA, 3PL, affiliate, dropshipping, or other monetization paths
- wants low operational cost during MVP development

## Product Positioning

This is not an FBA tool.

This is not a content generation tool.

This is not an inventory management system.

This is a **product identification and opportunity intelligence engine**.

## Core Questions

The system should help answer:

### Demand

- Is demand increasing?
- Is the trend recent or long-lived?
- Is demand seasonal?
- Which channels show demand?

### Competition

- How crowded is the market?
- Are there dominant brands?
- How many reviews do top products have?
- Are listings high-quality or poorly executed?

### Customer Pain

- What are customers complaining about?
- What features are missing?
- What improvements would justify a premium?
- Are complaints frequent enough to represent a real opportunity?

### Economics

- What is the expected selling price?
- What is the estimated unit cost?
- What are fulfillment costs?
- What is the estimated margin?
- Does the product still work after FBA/3PL fees?

### Risk

- Is the product regulated?
- Does it involve batteries, liquids, supplements, medical claims, or fragile components?
- Are there trademark/IP concerns?
- Would shipping or returns be difficult?

## Non-Goals

The MVP must not implement:

- AI content generation
- social posting
- affiliate automation
- Amazon listing creation
- supplier messaging
- inventory management
- order management
- paid ads automation
- automated purchasing
- automatic manufacturer negotiation

These can be future action plugins.

## Future Downstream Actions

The system may later recommend or initiate:

- FBA launch research
- 3PL launch research
- affiliate test
- dropshipping test
- supplier outreach
- landing page generation
- product listing generation
- marketing content generation

But the intelligence engine should remain independent of these actions.

## Strategic Moat

The moat is not the UI.

The moat is not a single API integration.

The moat is the product intelligence dataset:

```text
products
+ aliases
+ observations
+ trend histories
+ review insights
+ supplier economics
+ costs
+ scores
+ historical recommendations
```

Over time, this creates proprietary knowledge about what types of products become viable opportunities.
