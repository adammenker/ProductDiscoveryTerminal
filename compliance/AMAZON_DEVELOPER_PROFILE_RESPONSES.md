# Amazon Developer Profile Response Drafts

These drafts should be used only after the documented controls are actually in place for the environment where Amazon Information is processed. Do not claim production controls that are not implemented.

## Application Scope

Private internal product research and FBA unit-economics tool for my own Amazon seller account. The application uses Product Listing and Pricing roles only to retrieve catalog, pricing, and product fee-estimate data for comparable ASINs. It does not access buyer PII, order data, buyer messages, shipping addresses, tax data, or restricted role data.

## Primary Business Activity

My primary business activity on Amazon is researching and evaluating consumer products to sell through my own seller account. My private internal application will use Selling Partner API to retrieve catalog, pricing, and fee-estimate data for comparable ASINs to analyze product opportunities, estimate FBA fees, and calculate target landed costs. It will not access buyer PII, orders, messages, or tax data.

## Use Case

The application is a private internal product discovery and FBA unit-economics terminal. It identifies comparable Amazon catalog items, retrieves catalog attributes, retrieves pricing and offer information, retrieves product fee estimates, and combines those values with user-provided assumptions to calculate target maximum landed cost for supplier research. It is used only by the account owner/developer and is not offered to external sellers.

## Incident Response

Yes. I maintain an incident response plan with defined owner responsibilities, six-month review cadence, containment and credential rotation steps, log review, impact assessment, and 24-hour notification procedures. Any security incident involving Amazon Information will be reported to security@amazon.com within 24 hours of detection.

## Network Security

For local development, the application is private/internal, not publicly exposed, and keeps secrets local. Before production SP-API use in any non-local environment, the runtime must use HTTPS, firewall/security group restrictions, private database networking, IDS/IPS or managed threat detection, endpoint anti-virus/anti-malware, MFA-protected administrative access, and network segmentation separating public application access from database and secrets.

## Password and MFA Controls

Yes. Accounts that can access Amazon Information or production credentials must use MFA, unique non-shared accounts, passwords of at least 12 characters with special characters, and annual password/credential review and rotation at least every 365 days. Credentials are rotated immediately after suspected compromise.

## Credential Storage

Yes. SP-API credentials are backend-only, are not sent to the frontend, are not hardcoded, are not committed to source control, and are stored only in local ignored environment files or a secure password/secret manager. Sandbox and production credentials are kept separate and rotated at least annually.

