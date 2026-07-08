# Security Policy

Security owner: Adam Menker

## Scope

Product Discovery Terminal is private and internal only. It is used by the account owner/developer for product discovery, catalog research, pricing analysis, FBA fee estimates, and max landed-cost calculations.

The application does not provide third-party user access and must not be exposed as a public SaaS application.

## Credential Handling

- Amazon SP-API credentials are handled only by the backend.
- The frontend must never receive LWA client secrets, refresh tokens, access tokens, or other credentials.
- Secrets must not be committed to source control.
- Secrets must not be hardcoded in source files, documentation, tests, screenshots, issue trackers, or chat logs.
- `.env` files are local-only and ignored by git.
- `.env.example` may contain placeholder values only.
- Amazon credentials must be rotated at least annually and immediately after suspected compromise.

## Deployment Requirements

- HTTPS/TLS is required for any non-local deployment.
- Amazon Information must be encrypted in transit.
- The database must not be exposed to the public internet.
- Production secrets must be stored in a password manager, secret manager, or private deployment environment variables.
- Production systems must use firewall/access controls, monitoring, anti-malware/endpoint protection, and network segmentation appropriate to the deployment.

## Access Requirements

- MFA must be enabled on Amazon, GitHub, cloud provider, password manager, and other administrative accounts.
- Access to Amazon Information is restricted to approved users with a business need.
- No shared accounts are permitted.
- If future users are added, role-based access control must be implemented before access is granted.

## Production Guardrail

The backend includes a production startup guard. If `APP_ENV=production`, the API will fail fast unless `ALLOW_PUBLIC_UNAUTHENTICATED=true` is explicitly set. This prevents accidental public exposure of an unauthenticated internal tool.

