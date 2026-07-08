# Access Control Policy

Access owner: Adam Menker

## Current Access Model

- Only the primary account owner/developer has access to Product Discovery Terminal.
- Access to Amazon Information is restricted based on business need.
- No employees, contractors, third parties, or external sellers have access.
- No shared accounts are permitted.

If future users are added, role-based access control must be implemented before granting access. Each user must have an individual account, least-privilege access, and auditability.

## Password and MFA Requirements

All accounts that can access the application, source code, production environment, password manager, cloud provider, or Amazon developer/seller account must enforce:

- Minimum password length of 12 characters.
- Special characters required.
- Uppercase, lowercase, and numeric characters required where supported.
- MFA required.
- Password expiration or credential review at least every 365 days.
- Annual password and credential rotation review.
- Immediate password or credential rotation after suspected compromise.
- No reuse of compromised, shared, or default passwords.

## Access Review

Access must be reviewed at least annually and whenever:

- A new production environment is created.
- A device or account is suspected to be compromised.
- A new user, contractor, or service account is proposed.
- Amazon SP-API roles or scopes are changed.

Because the current application is single-owner, review consists of verifying that only Adam Menker has access to the repository, local environment, secret store, seller account, and production runtime.

