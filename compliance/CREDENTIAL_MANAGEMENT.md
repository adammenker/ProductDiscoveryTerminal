# Credential Management Policy

Credential owner: Adam Menker

## SP-API Credentials

Amazon LWA client secrets, refresh tokens, access tokens, and any future API keys are backend-only secrets.

They must never be:

- Committed to source control.
- Hardcoded into application source code.
- Stored in frontend code.
- Sent to the browser.
- Written into logs.
- Shared in screenshots, issue trackers, documentation, spreadsheets, or chat.
- Stored in public repositories.

## Storage

- `.env` files are local-only and ignored by git.
- `.env.example` must contain placeholder values only.
- Long-lived production secrets must be stored in a password manager, secret manager, or private deployment environment variables.
- Secret storage accounts must require MFA.
- Repositories should remain private.
- GitHub secret scanning should be enabled if this repository is hosted on GitHub.

## Rotation

- Amazon SP-API credentials must be rotated at least annually.
- Credentials must be rotated immediately after suspected exposure or compromise.
- Production and sandbox credentials must remain separate.
- Old credentials must be revoked after rotation is complete.

## Application Safeguards

- Backend config values are not exposed by API responses.
- Plugin status may report whether credentials are configured, but must not report credential values.
- Secret redaction is enabled for logs and structured data before logging.
- Tests verify placeholder-only environment examples and secret redaction behavior.

