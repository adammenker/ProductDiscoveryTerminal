# SP-API Production Readiness Spec

## Purpose

Prepare the Product Discovery Terminal for Amazon SP-API production access by implementing and documenting the security controls Amazon flagged during Developer Profile review.

This spec is for Codex to implement in the existing Product Discovery Terminal repository.

The goal is not to overbuild enterprise infrastructure. The goal is to truthfully support the security profile for a private internal seller application that uses Amazon SP-API for product research and FBA unit-economics analysis.

## Background

Amazon rejected the SP-API Developer Profile because the following controls were missing or answered incorrectly:

1. Incident response plan with defined roles, 6-month reviews, and 24-hour notification procedures.
2. Incident response plan must include reporting security incidents involving Amazon Information to `security@amazon.com` within 24 hours of detection.
3. Network security controls: firewalls, IDS/IPS, anti-virus/anti-malware, and network segmentation.
4. Password requirements: 12-character minimum with special characters, MFA, 365-day expiration, and annual rotation.

The application should remain scoped to:

- Private internal use.
- Own Amazon seller account only.
- Product Listing and Pricing roles only.
- No buyer PII.
- No order management.
- No buyer messages.
- No tax data.
- No restricted SP-API roles.

## High-Level Requirements

Codex should implement:

1. Compliance documentation.
2. Application security hardening.
3. Secret/credential management safeguards.
4. SP-API production-readiness configuration.
5. A compliance checklist page or command.
6. Tests to verify secrets are not exposed and security controls are documented.

## Non-Goals

Do not implement:

- Buyer PII access.
- Order ingestion.
- Buyer communication.
- Tax data access.
- Inventory/order management.
- Public SaaS user management.
- Complex enterprise security tooling unless necessary.
- AWS event-driven infrastructure.
- Content generation.

## Directory Structure

Add a `compliance/` folder at the repository root:

```text
compliance/
  README.md
  SECURITY.md
  ACCESS_CONTROL.md
  INCIDENT_RESPONSE.md
  NETWORK_SECURITY.md
  CREDENTIAL_MANAGEMENT.md
  AMAZON_DATA_HANDLING.md
  REVIEW_LOG.md
```

Also update:

```text
README.md
.env.example
.gitignore
backend/
frontend/
```

## Compliance Documentation Requirements

### 1. `compliance/README.md`

Explain:

- This application is a private internal product research tool.
- It uses Amazon SP-API only for catalog, pricing, and fee-estimate data.
- It does not access restricted buyer PII, orders, buyer messages, shipping addresses, or tax data.
- It is operated only by the account owner/developer.
- Security controls are documented in the compliance folder.

### 2. `compliance/SECURITY.md`

Include:

- Security owner: Adam Menker.
- Private/internal use only.
- No third-party users.
- Backend-only credential handling.
- No credentials in frontend.
- No secrets in source control.
- HTTPS required for any non-local deployment.
- Database must not be exposed to the public internet.
- Amazon Information must be encrypted in transit.
- Amazon credentials must be rotated at least annually or immediately after suspected compromise.
- MFA must be enabled on Amazon, GitHub, cloud provider, and password manager accounts.

### 3. `compliance/ACCESS_CONTROL.md`

Document:

- Only the primary account owner/developer has access.
- Access to Amazon Information is restricted based on business need.
- No employees, contractors, or third parties have access.
- If future users are added, role-based access control must be implemented before granting access.
- Password requirements:
  - minimum 12 characters
  - special characters required
  - MFA required
  - annual password/credential review
  - credential rotation at least every 365 days
- No shared accounts.

### 4. `compliance/INCIDENT_RESPONSE.md`

Create a real incident response plan.

Must include:

- Incident owner: Adam Menker.
- Backup owner: N/A while single-owner.
- Review cadence: every 6 months.
- Incident detection steps.
- Containment steps.
- Credential revocation/rotation steps.
- Log review steps.
- Impact assessment steps.
- Amazon Information exposure assessment.
- Notification procedure.

Must explicitly state:

```text
Any security incident involving Amazon Information will be reported to security@amazon.com within 24 hours of detection.
```

Include a checklist:

```text
1. Identify incident.
2. Contain affected system.
3. Revoke/rotate exposed credentials.
4. Determine whether Amazon Information was accessed, disclosed, altered, or lost.
5. Notify Amazon at security@amazon.com within 24 hours if Amazon Information is involved.
6. Document timeline, impact, and remediation.
7. Review controls and update this plan.
```

### 5. `compliance/NETWORK_SECURITY.md`

Document the required network controls.

For local development:

- App runs locally.
- Backend is not publicly exposed.
- `.env` secrets remain local.
- OS firewall should be enabled.
- Endpoint anti-malware/OS security protections should be enabled.
- Development database should bind only to localhost or Docker network.

For production/non-local deployment:

- HTTPS only.
- Firewall/security groups restrict inbound traffic.
- Backend API is the only public service if deployed.
- Database is private and not publicly exposed.
- Admin access protected by MFA.
- Secrets stored in a secret manager or private environment variables.
- IDS/monitoring must be enabled using an appropriate provider or host/cloud security tool.
- Network segmentation must separate public app access from database/secrets.

Important: The app should not claim production network controls unless deployment docs/config actually support them.

### 6. `compliance/CREDENTIAL_MANAGEMENT.md`

Document:

- LWA client secret and refresh token are backend-only.
- Secrets must never be committed.
- Secrets must never be logged.
- Secrets must never be sent to frontend.
- `.env` must be gitignored.
- `.env.example` must contain placeholder values only.
- Use a password manager or secret manager for long-lived secrets.
- Rotate secrets annually and after suspected exposure.
- Enable GitHub secret scanning if repository is hosted on GitHub.

### 7. `compliance/AMAZON_DATA_HANDLING.md`

Document:

- What Amazon data the app accesses:
  - catalog data
  - comparable ASIN metadata
  - pricing/offer information
  - product fee estimates
- What Amazon data the app does not access:
  - buyer PII
  - buyer messages
  - order/customer details
  - shipping addresses
  - tax data
  - restricted role data
- Data usage:
  - internal product opportunity research
  - FBA fee modeling
  - margin analysis
  - max landed cost calculation
- Data retention:
  - retain only data needed for product research
  - allow deletion/reset of local database
- Data sharing:
  - no third-party sharing
  - no public exposure

### 8. `compliance/REVIEW_LOG.md`

Add a simple review log table:

```markdown
| Date | Reviewer | Documents Reviewed | Changes Made | Next Review Due |
|---|---|---|---|---|
| YYYY-MM-DD | Adam Menker | Incident Response, Access Control, Network Security | Initial version | YYYY-MM-DD |
```

The next review date should be 6 months later.

## Application Security Implementation Requirements

### 1. Environment Variables

Update `.env.example` with placeholders only:

```env
AMAZON_SP_API_ENV=sandbox
AMAZON_SP_API_ENDPOINT=https://sandbox.sellingpartnerapi-na.amazon.com
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER
AMAZON_LWA_CLIENT_ID=replace_me
AMAZON_LWA_CLIENT_SECRET=replace_me
AMAZON_LWA_REFRESH_TOKEN=replace_me
```

Ensure `.gitignore` includes:

```text
.env
.env.*
!.env.example
```

### 2. Secret Redaction

Implement a utility that redacts sensitive values from logs.

Sensitive keys include:

```text
token
secret
password
refresh_token
access_token
client_secret
authorization
x-amz-access-token
```

All logs that include config, request headers, errors, or API responses must pass through this redaction utility.

### 3. Backend-Only Credentials

Ensure:

- SP-API credentials are only read in backend.
- Frontend never receives LWA credentials, refresh tokens, access tokens, or client secrets.
- API endpoints must not return environment/config secrets.
- Plugin status endpoints may return `configured: true/false`, but never secret values.

Example safe response:

```json
{
  "plugin": "amazon_spapi",
  "configured": true,
  "environment": "sandbox",
  "missing_credentials": []
}
```

### 4. SP-API Environment Mode

Support both:

```text
sandbox
production
```

Behavior:

- sandbox uses sandbox endpoint
- production uses production endpoint
- credentials come from env vars
- missing credentials disable Amazon plugins gracefully
- plugin failure should result in partial pipeline failure, not app crash

### 5. Access Control for Current MVP

Because this is a private local/internal tool:

- Do not add multi-user auth unless already present.
- Add a clear warning if the app is deployed without auth.
- For any non-local deployment, require at least a simple admin auth mechanism or deployment-layer access control before exposing the app publicly.

Add a config variable:

```env
ALLOW_PUBLIC_UNAUTHENTICATED=false
```

If app is running in production mode and this is false, frontend/API should not be exposed without auth or should show a startup warning/fail-fast.

### 6. HTTPS Requirement

Document that production must use HTTPS.

If the backend has environment awareness, add a warning when:

```text
APP_ENV=production
```

and the configured public URL is not HTTPS.

Do not block local development on HTTPS.

## Optional Compliance Status Endpoint

Add an internal endpoint:

```text
GET /security/compliance-status
```

Return:

```json
{
  "amazon_spapi_env": "sandbox",
  "amazon_credentials_configured": true,
  "incident_response_doc_exists": true,
  "network_security_doc_exists": true,
  "access_control_doc_exists": true,
  "credential_management_doc_exists": true,
  "amazon_data_handling_doc_exists": true,
  "secrets_redaction_enabled": true
}
```

This endpoint must not expose secrets.

If adding this endpoint feels unnecessary, implement a CLI command instead:

```bash
python -m app.security.compliance_check
```

## Tests

Add or update tests for:

### Secret Handling

- `.env.example` contains no real secrets.
- plugin config/status does not expose secrets.
- log redaction removes tokens/secrets.
- frontend API responses do not include credential values.

### Amazon Plugin Safety

- missing Amazon credentials disables plugin gracefully.
- sandbox mode uses sandbox endpoint.
- production mode uses production endpoint.
- Amazon plugin errors create failed plugin runs, not app crashes.

### Compliance Docs

- required files exist.
- `INCIDENT_RESPONSE.md` contains `security@amazon.com`.
- `INCIDENT_RESPONSE.md` contains `24 hours`.
- `REVIEW_LOG.md` exists.
- `ACCESS_CONTROL.md` contains MFA and 12-character minimum.
- `NETWORK_SECURITY.md` mentions firewall, IDS/IPS, anti-malware, and segmentation.

## Developer Profile Resubmission Support

Add `compliance/AMAZON_DEVELOPER_PROFILE_RESPONSES.md` with suggested answer drafts.

### Application Scope

```text
Private internal product research and FBA unit-economics tool for my own Amazon seller account. The application uses Product Listing and Pricing roles only to retrieve catalog, pricing, and product fee-estimate data for comparable ASINs. It does not access buyer PII, order data, buyer messages, shipping addresses, tax data, or restricted role data.
```

### Primary Business Activity, <=500 characters

```text
My primary business activity on Amazon is researching and evaluating consumer products to sell through my own seller account. My private internal application will use Selling Partner API to retrieve catalog, pricing, and fee-estimate data for comparable ASINs to analyze product opportunities, estimate FBA fees, and calculate target landed costs. It will not access buyer PII, orders, messages, or tax data.
```

### Use Case

```text
The application is a private internal product discovery and FBA unit-economics terminal. It identifies comparable Amazon catalog items, retrieves catalog attributes, retrieves pricing and offer information, retrieves product fee estimates, and combines those values with user-provided assumptions to calculate target maximum landed cost for supplier research. It is used only by the account owner/developer and is not offered to external sellers.
```

### Security Controls

Include concise descriptions of implemented controls only after they are actually implemented/documented.

## Codex Implementation Order

1. Create compliance folder and documentation.
2. Update `.env.example` and `.gitignore`.
3. Add secret redaction utility.
4. Audit backend logging/config responses to ensure secrets are never exposed.
5. Add Amazon plugin environment handling if missing.
6. Add plugin disabled state for missing credentials.
7. Add compliance status endpoint or CLI command.
8. Add tests for compliance docs and secret handling.
9. Update README with SP-API sandbox/production setup notes.
10. Stop. Do not add new external APIs.

## Acceptance Criteria

This work is complete when:

- All compliance documents exist.
- Incident response plan explicitly includes 24-hour reporting to `security@amazon.com`.
- Access control document includes 12-character password minimum, special characters, MFA, 365-day/annual rotation.
- Network security document covers firewalls, IDS/IPS, anti-malware, and segmentation.
- Credential management document covers no hardcoding, no public repos, no sharing, no frontend exposure.
- `.env` files are ignored.
- `.env.example` has placeholders only.
- Logs redact secrets.
- Frontend cannot access secrets.
- Amazon plugins fail safely when credentials are missing.
- Tests pass.
